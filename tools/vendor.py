import os
import re
import tarfile
import zipfile
import urllib.request
import shutil
import subprocess
import hashlib

VENDOR_DIR = os.path.abspath("vendor")
RULES_ROS2_DIR = os.path.abspath("rules_ros2")
PATCHES_DIR = os.path.join(RULES_ROS2_DIR, "repositories/patches")

def parse_bzl(file_path):
    repos = []
    with open(file_path, 'r') as f:
        content = f.read()
    
    matches = re.finditer(r'maybe\s*\(\s*http_archive\s*,\s*name\s*=\s*"([^"]+)"(.*?)\)', content, re.DOTALL)
    
    for m in matches:
        name = m.group(1)
        body = m.group(2)
        
        repo = {"name": name}
        
        url_match = re.search(r'url\s*=\s*"([^"]+)"', body)
        urls_match = re.search(r'urls\s*=\s*\[\s*"([^"]+)"', body)
        sha_match = re.search(r'sha256\s*=\s*"([^"]+)"', body)
        strip_match = re.search(r'strip_prefix\s*=\s*"([^"]+)"', body)
        build_file_match = re.search(r'build_file\s*=\s*"@com_github_mvukov_rules_ros2//repositories:([^"]+)"', body)
        
        patches = []
        patches_match = re.search(r'patches\s*=\s*\[(.*?)\]', body, re.DOTALL)
        if patches_match:
            p_content = patches_match.group(1)
            p_iter = re.finditer(r'"@com_github_mvukov_rules_ros2//repositories/patches:([^"]+)"', p_content)
            for p in p_iter:
                patches.append(p.group(1))
        
        # Parse patch_args
        patch_args = []
        patch_args_match = re.search(r'patch_args\s*=\s*\[(.*?)\]', body, re.DOTALL)
        if patch_args_match:
            args_content = patch_args_match.group(1)
            # simplistic parsing of strings like "-p1"
            args_iter = re.finditer(r'"([^"]+)"', args_content)
            for a in args_iter:
                patch_args.append(a.group(1))

        repo["url"] = url_match.group(1) if url_match else (urls_match.group(1) if urls_match else None)
        repo["sha256"] = sha_match.group(1) if sha_match else None
        repo["strip_prefix"] = strip_match.group(1) if strip_match else None
        repo["build_file"] = build_file_match.group(1) if build_file_match else None
        repo["patches"] = patches
        repo["patch_args"] = patch_args
        
        repos.append(repo)
    return repos

def download_and_extract(repo):
    name = repo["name"]
    dest_dir = os.path.join(VENDOR_DIR, name)
    
    if os.path.exists(dest_dir):
        # Check if already patched? Hard to say. 
        # Assume if dir exists and we are re-running, maybe we should wipe it if we suspect corruption?
        # For now, let's skip if looks valid, but since we had a failure, 
        # we might want to force overwrite for the failed one.
        # Simple heuristic: look for BUILD.bazel.
        if os.path.exists(os.path.join(dest_dir, "BUILD.bazel")) or os.path.exists(os.path.join(dest_dir, "BUILD")):
             print(f"Skipping {name}, already vendored.")
             return
        else:
             print(f"Directory {name} exists but incomplete. Re-vendoring.")
             shutil.rmtree(dest_dir)

    print(f"Vendoring {name}...")
    
    url = repo["url"]
    if not url:
        print(f"Error: No URL for {name}")
        return

    filename = url.split('/')[-1]
    filepath = os.path.join(VENDOR_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"  Downloading {url}...")
        urllib.request.urlretrieve(url, filepath)
    
    if repo["sha256"]:
        with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != repo["sha256"]:
            print(f"  Error: SHA256 mismatch for {name}. Expected {repo['sha256']}, got {digest}")
            return

    print(f"  Extracting...")
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            with tarfile.open(filepath, "r:gz") as tar:
                def members(tf):
                    prefix = repo["strip_prefix"]
                    for member in tf.getmembers():
                        if prefix and member.path.startswith(prefix):
                            member.path = member.path[len(prefix):].lstrip('/')
                        elif prefix:
                             continue
                        yield member
                tar.extractall(dest_dir, members=members(tar))
        elif filename.endswith(".zip"):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                prefix = repo["strip_prefix"]
                for info in zip_ref.infolist():
                    if prefix and info.filename.startswith(prefix):
                        extract_path = info.filename[len(prefix):].lstrip('/')
                        if not extract_path: continue
                        target = os.path.join(dest_dir, extract_path)
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        if not info.is_dir():
                            with open(target, 'wb') as f:
                                f.write(zip_ref.read(info))
                    elif not prefix:
                         zip_ref.extract(info, dest_dir)
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    os.remove(filepath)

    for patch in repo["patches"]:
        patch_path = os.path.join(PATCHES_DIR, patch)
        print(f"  Applying patch {patch}...")
        
        args = ["patch", "-i", patch_path]
        if repo["patch_args"]:
            args.extend(repo["patch_args"])
        else:
            args.append("-p0") # Default to -p0 if not specified, assuming exact match or relative

        # Try applying patch. If it fails with default args, try fallback strategies
        # Force non-interactive with "--forward" or "--batch" if available, but "-N" is standard
        # However, passing input=b'\n' handles prompt fallback to fail.
        
        try:
            subprocess.run(args, cwd=dest_dir, check=True, input=b'\n')
        except subprocess.CalledProcessError:
            print(f"  Patch failed with args {args}. Retrying with -p0...")
            try:
                subprocess.run(["patch", "-p0", "-i", patch_path], cwd=dest_dir, check=True, input=b'\n')
            except subprocess.CalledProcessError:
                 print(f"  Patch failed with -p0. Retrying with -p1...")
                 subprocess.run(["patch", "-p1", "-i", patch_path], cwd=dest_dir, check=True, input=b'\n')

    if repo["build_file"]:
        src_build = os.path.join(RULES_ROS2_DIR, "repositories", repo["build_file"])
        dst_build = os.path.join(dest_dir, "BUILD.bazel")
        print(f"  Copying BUILD file {repo['build_file']}...")
        shutil.copy(src_build, dst_build)

def main():
    ros2_repos_impl = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/ros2_repositories_impl.bzl"))
    ros2_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/repositories.bzl"))
    third_party_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/third_party_repositories.bzl"))
    rust_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/rust_setup_stage_1.bzl"))
    
    for repo in ros2_repos_impl + ros2_repos + third_party_repos + rust_repos:
        download_and_extract(repo)

if __name__ == "__main__":
    main()