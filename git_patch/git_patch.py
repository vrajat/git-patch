#!/usr/bin/python
import argparse
import os
import logging
import re
import subprocess
from subprocess import CalledProcessError
import sys
import yaml

_current_version = 1
_supported_versions = [1]


def _log_init():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def _head(branch):
    output = subprocess.Popen(['git', 'show-ref', 'refs/heads/%s' % branch], stdout=subprocess.PIPE).communicate()[0]
    return output.split(' ')[0]


def _write_config(patches):
    with open('.patch/config.yml', 'w') as outfile:
        outfile.write(yaml.dump(patches, default_flow_style=False))


def init(args, patches):
    config = {
        "tracking": {
            "branch": args.branch,
            "commit-id": _head(args.branch)
        },
        "sections": [
            {
                "name": "unclassified",
                "commits": []
            }
        ],
        "version": _current_version
    }
    if not os.path.exists(".patch"):
        os.makedirs(".patch")

    _write_config(config)


def create_branch(args, patches):
    try:
        subprocess.check_call(["git", "branch", "-D", args.name])
    except CalledProcessError as err:
        logging.debug("Branch %s does not exist" % args.name)
    subprocess.check_call(["git", "checkout", "-b", args.name])
    subprocess.check_call(["git", "fetch", "upstream"])
    subprocess.check_call(["git", "rebase", args.remote])
    logging.info("Create and rebased branch %s" % args.name)


def generate(args, patches):
    current = patches["tracking"]["commit-id"]
    head = _head(patches["tracking"]["branch"])
    logging.debug("Current: %s, Head: %s" % (current, head))

    generated = subprocess.Popen(['git', 'format-patch', '%s..%s' % (current, head), "-o", ".patch"],
                                 stdout=subprocess.PIPE).communicate()[0]

    commit_list = generated.splitlines(False)
    logging.info("%d commits processed." % len(commit_list))
    patches["tracking"]["commit-id"] = head
    unclassified = None
    for p in patches["sections"]:
        if p["name"] == "unclassified":
            unclassified = p
            break

    for p in commit_list:
        unclassified["commits"].append(os.path.basename(p))

    _write_config(patches)


def list_patches(args, patches):
    print "\n".join([s["name"] for s in patches["sections"]])


def create_section(args, patches):
    patches["sections"].append({
        "name": args.name,
        "commits": []
    })

    _write_config(patches)


def move_patch(args, patches):
    # Find the patch
    found = False
    for section in patches["sections"]:
        if args.patch in section["commits"]:
            found = True
            section["commits"].remove(args.patch)
            break

    if found:
        found_section = False
        for section in patches["sections"]:
            if section["name"] == args.to:
                section["commits"].append(args.patch)
                found_section = True
                break
        if not found_section:
            raise Exception("Section `%s` not found" % args.to)
    else:
        raise Exception("Patch `%s` not found" % args.patch)

    _write_config(patches)


def patch_apply(args, patches):
    for section in patches["sections"]:
        d = vars(args)
        d['section'] = section
        section_apply(args, patches)


def patch_commits(args, patches):
    print "\n".join(args.section["commits"])


def section_apply(args, patches):
    number = re.compile("^\d+-")
    for commit in args.section["commits"]:
        logging.info("Processing: %s " % commit)
        subject = number.sub("", commit).replace(".patch", "").replace("-", " ")
        subprocess.check_call(["git", "apply", "-3", ".patch/%s" % commit])
        subprocess.check_call(["git", "commit", "-m", "[Patch] %s" % subject])


def edit(args, patches):
    def begin_edit():
        subject_re = re.compile("Subject: \[PATCH.*\] (.*)^\-\-\-\n", re.S | re.M)
        edit_section = args.section
        for section in patches["sections"]:
            if section["name"] == edit_section["name"]:
                break
            logging.info("Processing section %s" % section["name"])
            d = vars(args)
            d['section'] = section
            section_apply(args, patches)

        for commit in edit_section["commits"]:
            logging.info("Processing: %s " % commit)
            with open('.patch/%s' % commit, 'r') as commit_file:
                data = commit_file.read()
            subject = subject_re.search(data).group(1)
            logging.info(subject)
            try:
                subprocess.check_call(["git", "apply", "-3", ".patch/%s" % commit])
            except CalledProcessError as err:
                logging.error("%s failed to apply" % commit)
                if commit != args.patch:
                    raise err
            if commit == args.patch:
                break
            subprocess.check_call(["git", "commit", "-m", "[Patch] %s" % subject])

        head = subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                 stdout=subprocess.PIPE).communicate()[0].strip()
        # Write metadata to .patch/begin_edit.yml
        metadata = {
            "patch": args.patch,
            "head": head,
            "subject": subject
        }
        with open('.patch/metadata_edit.yml', 'w') as outfile:
            outfile.write(yaml.dump(metadata, default_flow_style=False))

    def complete_edit():
        with open(".patch/metadata_edit.yml") as yml:
            metadata = yaml.safe_load(yml)
        logging.debug(metadata)
        subprocess.check_call(["git", "commit", "-m", metadata['subject']])
        generated = subprocess.Popen(['git', 'format-patch', '%s..HEAD' % metadata['head'], "-o", ".patch"],
                                 stdout=subprocess.PIPE).communicate()[0]
        logging.debug(generated)
        commit_list = generated.splitlines()
        assert(len(commit_list) == 1)
        logging.info("Move %s to .patch/%s" % (commit_list[0], metadata['patch']))
        os.rename("%s" % commit_list[0], ".patch/%s" % metadata['patch'])
        os.unlink(".patch/metadata_edit.yml")

    if args.patch is not None:
        begin_edit()
    else:
        complete_edit()


def main():
    _log_init()
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers()

    init_parser = sub_parsers.add_parser("init", help="Initialize branch which will be patched")
    init_parser.add_argument("-b", "--branch", required=True, help="Development branch")
    init_parser.set_defaults(func=init)

    branch_parser = sub_parsers.add_parser("create-branch", help="Create a new development branch")
    branch_parser.add_argument("-n", "--name", help="Name of branch", default="git_patch")
    branch_parser.add_argument("-r", "--remote", help="Name of Git Remote", default="upstream/master")
    branch_parser.set_defaults(func=create_branch)

    list_parser = sub_parsers.add_parser("list", help="List all patches")
    list_parser.set_defaults(func=list_patches)

    generate_parser = sub_parsers.add_parser("generate", help="Generate patches from tracked branch")
    generate_parser.set_defaults(func=generate)

    create_section_parser = sub_parsers.add_parser("create-section", help="Create a new patch section")
    create_section_parser.add_argument("-n", "--name", required=True, help="Name of section")
    create_section_parser.set_defaults(func=create_section)

    move_patch_parser = sub_parsers.add_parser("move-patch", help="Move patch to a new section")
    move_patch_parser.add_argument("-p", "--patch", required=True, help="File name of patch")
    move_patch_parser.add_argument("-t", "--to", required=True, help="Name of destination section")
    move_patch_parser.set_defaults(func=move_patch)

    patch_apply_parser = sub_parsers.add_parser("apply", help="Apply all patch")
    patch_apply_parser.set_defaults(func=patch_apply)

    patches = None

    if os.path.exists(".patch/config.yml"):
        with open(".patch/config.yml") as yml:
            patches = yaml.safe_load(yml)

        if 'version' not in patches:
            patches['version'] = _current_version

        for s in patches["sections"]:
            p = sub_parsers.add_parser(s["name"], help="Operations for %s" % s["name"])
            sub_sub = p.add_subparsers()
            sub_list = sub_sub.add_parser("list", help="List all commits")
            sub_list.set_defaults(func=patch_commits, section=s)

            sub_apply = sub_sub.add_parser("apply", help="Apply a patch")
            sub_apply.set_defaults(func=section_apply, section=s)

            edit_parser = sub_sub.add_parser("edit", help="Begin editing a patch")
            edit_group = edit_parser.add_mutually_exclusive_group(required=True)
            edit_group.add_argument("-p", "--patch", help="File name of patch")
            edit_group.add_argument("-c", "--commit", action="store_true", help="Commit the edit")
            edit_parser.set_defaults(func=edit, section=s)

    argument = parser.parse_args()
    argument.func(argument, patches)

if __name__ == "__main__":
    main()
