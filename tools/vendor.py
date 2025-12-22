import os
import tarfile
import zipfile
import urllib.request
import shutil
import subprocess
import hashlib
import base64
import binascii
import sys
import ast

VENDOR_DIR = os.path.abspath("vendor")
RULES_ROS2_DIR = os.path.abspath("rules_ros2")
PATCHES_DIR = os.path.join(RULES_ROS2_DIR, "repositories/patches")

def get_arg_value(keyword):
    if isinstance(keyword.value, ast.Constant):
        return keyword.value.value
    elif isinstance(keyword.value, ast.List):
        return [elt.value for elt in keyword.value.elts if isinstance(elt, ast.Constant)]
    elif isinstance(keyword.value, ast.Dict):
        result = {}
        for k, v in zip(keyword.value.keys, keyword.value.values):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                result[k.value] = v.value
        return result
    return None

def parse_bzl(file_path):
    repos = []
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found.")
        return repos

    with open(file_path, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Error parsing {file_path}: {e}")
        return repos

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'maybe':
            # Check if first arg is http_archive
            if len(node.args) > 0 and isinstance(node.args[0], ast.Name) and node.args[0].id == 'http_archive':
                repo = {}
                for keyword in node.keywords:
                    arg_name = keyword.arg
                    value = get_arg_value(keyword)
                    
                    if arg_name == 'name':
                        repo['name'] = value
                    elif arg_name == 'url':
                        repo['url'] = value
                    elif arg_name == 'urls':
                        # Prefer the first URL if multiple
                        if value and len(value) > 0:
                            repo['url'] = value[0]
                    elif arg_name == 'sha256':
                        repo['sha256'] = value
                    elif arg_name == 'integrity':
                        repo['integrity'] = value
                    elif arg_name == 'strip_prefix':
                        repo['strip_prefix'] = value
                    elif arg_name == 'build_file':
                        # Extract relative path from label string if possible
                        if value and value.startswith("@com_github_mvukov_rules_ros2//repositories:"):
                            repo['build_file'] = value.split(":")[-1]
                    elif arg_name == 'patches':
                        # Extract patch filenames from labels
                        patches = []
                        if value:
                            for p in value:
                                if "//repositories/patches:" in p:
                                    patches.append(p.split(":")[-1])
                        repo['patches'] = patches
                    elif arg_name == 'patch_args':
                        repo['patch_args'] = value
                    elif arg_name == 'remote_patches':
                        repo['remote_patches'] = value
                    elif arg_name == 'remote_patch_strip':
                        repo['remote_patch_strip'] = value
                    elif arg_name == 'remote_module_file_urls':
                        repo['remote_module_file_urls'] = value

                # Normalize defaults
                if 'patches' not in repo: repo['patches'] = []
                if 'patch_args' not in repo: repo['patch_args'] = []
                if 'remote_patches' not in repo: repo['remote_patches'] = {}
                if 'remote_patch_strip' not in repo: repo['remote_patch_strip'] = 0
                if 'remote_module_file_urls' not in repo: repo['remote_module_file_urls'] = []
                
                if 'name' in repo:
                    repos.append(repo)

    return repos

def verify_integrity(filepath, expected_integrity):
    if not expected_integrity:
        return True
    
    if expected_integrity.startswith("sha256-"):
        # SRI format
        with open(filepath, "rb") as f:
            digest_bytes = hashlib.sha256(f.read()).digest()
        
        # Decode expected SRI
        try:
            expected_bytes = base64.b64decode(expected_integrity[7:])
        except binascii.Error:
            print(f"  Error: Invalid SRI format {expected_integrity}")
            return False

        if digest_bytes != expected_bytes:
            print(f"  Error: SRI mismatch. Expected {expected_integrity}")
            return False
        return True
    else:
        # Assuming plain hex sha256
         with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
         if digest != expected_integrity:
            print(f"  Error: SHA256 mismatch. Expected {expected_integrity}, got {digest}")
            return False
         return True

def download_file(url, filepath, integrity=None, sha256=None):
    if not os.path.exists(filepath):
        print(f"  Downloading {url}...")
        try:
            urllib.request.urlretrieve(url, filepath)
        except Exception as e:
            print(f"  Error downloading {url}: {e}")
            return False

    if integrity:
        if not verify_integrity(filepath, integrity):
             os.remove(filepath)
             return False
    elif sha256:
        with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != sha256:
            print(f"  Error: SHA256 mismatch. Expected {sha256}, got {digest}")
            os.remove(filepath)
            return False
    return True

def download_and_extract(repo):
    name = repo["name"]
    dest_dir = os.path.join(VENDOR_DIR, name)
    
    if os.path.exists(dest_dir):
        # Heuristic check
        if os.path.exists(os.path.join(dest_dir, "BUILD.bazel")) or os.path.exists(os.path.join(dest_dir, "BUILD")) or os.path.exists(os.path.join(dest_dir, "MODULE.bazel")):
             print(f"Skipping {name}, already vendored.")
             return
        else:
             print(f"Directory {name} exists but incomplete. Re-vendoring.")
             shutil.rmtree(dest_dir)

    print(f"Vendoring {name}...")
    
    url = repo.get("url")
    if not url:
        print(f"Error: No URL for {name}")
        return

    os.makedirs(VENDOR_DIR, exist_ok=True)

    filename = url.split('/')[-1]
    if "?" in filename:
        filename = filename.split('?')[0]
    
    # Prefix with repo name to avoid collisions and generic names
    filename = f"{name}_{filename}"
    filepath = os.path.join(VENDOR_DIR, filename)
    
    if not download_file(url, filepath, integrity=repo.get("integrity"), sha256=repo.get("sha256")):
        return

    print(f"  Extracting...")
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        if filename.endswith(".tar.gz") or filename.endswith(".tgz") or filename.endswith(".tar.xz"):
            # tarfile handles xz if lzma is available (standard in py3)
            with tarfile.open(filepath, "r:*") as tar:
                def members(tf):
                    prefix = repo.get("strip_prefix")
                    for member in tf.getmembers():
                        if prefix:
                             if member.path.startswith(prefix):
                                  member.path = member.path[len(prefix):].lstrip('/')
                             else:
                                  continue
                        yield member
                tar.extractall(dest_dir, members=members(tar))
        elif filename.endswith(".zip"):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                prefix = repo.get("strip_prefix")
                for info in zip_ref.infolist():
                    if prefix:
                        if info.filename.startswith(prefix):
                            extract_path = info.filename[len(prefix):].lstrip('/')
                            if not extract_path: continue
                            target = os.path.join(dest_dir, extract_path)
                            os.makedirs(os.path.dirname(target), exist_ok=True)
                            if not info.is_dir():
                                with open(target, 'wb') as f:
                                    f.write(zip_ref.read(info))
                    else:
                         zip_ref.extract(info, dest_dir)
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    os.remove(filepath)

    # Apply local patches
    for patch in repo["patches"]:
        patch_path = os.path.join(PATCHES_DIR, patch)
        print(f"  Applying local patch {patch}...")
        
        args = ["patch", "-i", patch_path]
        if repo["patch_args"]:
            args.extend(repo["patch_args"])
        else:
            args.append("-p0")
        
        # Non-interactive and batch mode
        args.append("-N")
        args.append("-t")

        try:
            subprocess.run(args, cwd=dest_dir, check=True, input=b'\n')
        except subprocess.CalledProcessError:
            print(f"  Patch failed with args {args}. Retrying with -p0...")
            try:
                subprocess.run(["patch", "-p0", "-N", "-t", "-i", patch_path], cwd=dest_dir, check=True, input=b'\n')
            except subprocess.CalledProcessError:
                 print(f"  Patch failed with -p0. Retrying with -p1...")
                 try:
                    subprocess.run(["patch", "-p1", "-N", "-t", "-i", patch_path], cwd=dest_dir, check=True, input=b'\n')
                 except:
                    print("Patch failed.")

    # Apply remote patches
    for patch_url, patch_integrity in repo["remote_patches"].items():
        patch_filename = f"patch_{hashlib.md5(patch_url.encode()).hexdigest()}.patch"
        patch_path = os.path.join(VENDOR_DIR, patch_filename)
        print(f"  Downloading remote patch {patch_url}...")
        if download_file(patch_url, patch_path, integrity=patch_integrity):
            print(f"  Applying remote patch...")
            p_strip = repo.get("remote_patch_strip", 0)
            args = ["patch", f"-p{p_strip}", "-N", "-t", "-i", patch_path]
            try:
                subprocess.run(args, cwd=dest_dir, check=True, input=b'\n')
            except subprocess.CalledProcessError:
                print(f"  Remote patch failed with -p{p_strip}. Trying -p0...")
                subprocess.run(["patch", "-p0", "-N", "-t", "-i", patch_path], cwd=dest_dir, check=True, input=b'\n')
            
            os.remove(patch_path)

            # Special handling for llvm-project overlay
            if name == "llvm-project" and patch_url.endswith("0002-Add-LLVM-Bazel-overlay-files.patch"):
                print("  Applying llvm-project overlay manually...")
                overlay_dir = os.path.join(dest_dir, "utils", "bazel", "llvm-project-overlay")
                if os.path.exists(overlay_dir):
                    for root, dirs, files in os.walk(overlay_dir):
                        for file in files:
                            src_file = os.path.join(root, file)
                            rel_path = os.path.relpath(src_file, overlay_dir)
                            dst_file = os.path.join(dest_dir, rel_path)
                            
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            # Overwrite if exists
                            if os.path.exists(dst_file):
                                os.remove(dst_file)
                            shutil.move(src_file, dst_file)

    # Download remote module file
    for url in repo["remote_module_file_urls"]:
        print(f"  Downloading MODULE.bazel from {url}...")
        mod_path = os.path.join(dest_dir, "MODULE.bazel")
        download_file(url, mod_path)


    if repo.get("build_file"):
        src_build = os.path.join(RULES_ROS2_DIR, "repositories", repo["build_file"])
        dst_build = os.path.join(dest_dir, "BUILD.bazel")
        print(f"  Copying BUILD file {repo['build_file']}...")
        shutil.copy(src_build, dst_build)

def main():
    ros2_repos_impl = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/ros2_repositories_impl.bzl"))
    ros2_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/repositories.bzl"))
    third_party_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/third_party_repositories.bzl"))
    rust_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/rust_setup_stage_1.bzl"))
    bcr_repos = parse_bzl(os.path.join(RULES_ROS2_DIR, "repositories/bcr_repos.bzl"))
    
    for repo in ros2_repos_impl + ros2_repos + third_party_repos + rust_repos + bcr_repos:
        download_and_extract(repo)

if __name__ == "__main__":
    main()