# git-patch
An iterative rebase to manage open source forks.

Open Source project forks contain custom changes. Git Patch command helps manage the commits made on a 
fork in a structured manner.
git-patch support the following development model:
* OSS project has a master branch and tracks releases with tags or branches. 
* Forked project's development branch is a copy of a release branch or tag. 

The requirements of a patch management system are:  
1. Apply and test patches on HEAD of `upstream/master`.  
   Similar to CI, the patch system should facilitate detection of conflicts and unit test failures at regular intervals.
   Such a setup will help developers react to failures quickly and regularly.  
2. Allow skipping of some patches.  
   If conflicts or test failures are detected, developers should be able to skip or comment out some patches instead
   being forced to fix it. This requirement enables beta releases with some features missing.  
3. Patch management functions.  
   Provide functions to edit, combine and remove patches.  
   
For e.g. developers at Qubole, use the following model to develop on Apache Calcite.

Apache Calcite has a master branch and tags (as well as branches) for each release.  

- Qubole developers create a branch from tag `calcite-1.12.0` - `q-calcite-12` which is the development branch. All feature branches are merged to `q-calcite-12`.  
- Qubole developers want to continously test custom features on the master branch to ensure compatibility in future releases.  
- They created `oss-master` which is a mirror of `master` in apache/calcite`.

git-patch is used to manage patches and apply them on oss-master to test compatibility.
Check [qubole/calcite](https://github.com/qubole/incubator-calcite/tree/oss-master/.patch) for an example.


## Install
    pip install git-patch
        
        
## Setup Local Repository
    
    git remote add upstream <git url for upstream project>
    git fetch upstream

## Initialize Repository for patches

    git checkout upstream/master
    git checkout -b oss-master
    git patch init -b <development branch>
    git add .patch
    git commit -m "Add patch configuration"
    git push -u origin oss-master
    

## Generate patches

    git checkout oss-master
    git patch generate
    
## Create a development branch    

    # Creates a branch `git_patch` and rebases it upstream/master
    git patch create-branch
    
## Apply patches

    git checkout oss-master
    git patch apply
    
## Fix Conflicts
If a patch has conflicts, `apply` command will fail. The conflicts have to be resolved
and the patch has to be regenerated using the following commands:

    # Fix conflicts
    # IMPORTANT: All changes should be cached. 
    # IMPORTANT Do not commit any changes. 
    git patch fix-patch
        
    # If all steps are successful, a modified patch is available. 
    # Copy the patch to oss-master and commit it. 
    git checkout oss-master
    git add .patch/<patch file name>
    git commit

## Edit Patches
To edit a patch, use `apply` command will fail. Make edits and regenerate the patch. 

    git patch apply --patch <patch filename | path to patch>
    
    # Make edits
    # IMPORTANT: All changes should be cached. 
    # IMPORTANT Do not commit any changes. 
    git patch fix-patch
        
    # If all steps are successful, a modified patch is available. 
    # Copy the patch to oss-master and commit it. 
    git checkout oss-master
    git add .patch/<patch file name>
    git commit
    
## Squash commits in a section
Commits in a section can be squashed to a single commit. This is useful when there is no 
advantage in maintaining separate patches for a single feature or section. For e.g. lets say
a feature has the following patches:

- 0001-new-Add-new-feature.patch
- 0001-fix-Fix-a-bug-in-new-feature.patch
- 0001-new-redesign-internal-data-structures

Once this feature has stabilized, these patches can be squashed to a single one.


    # Create a development branch
    git patch create-branch
    
    # Squash commits in a section.
    # Commit message from the specified patch file is copied.
    git patch <section> squash --patch <patch file>
    
    