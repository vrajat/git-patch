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
   
For e.g. developers at Qubole, use the following model to develop on Facebook Presto.

PrestoDb has a master branch and tags for each release.
Qubole developers create a branch from tag `0.150` - `q-presto-0.150` which is the development branch.
All feature branches are merged to `q-presto-0.150`. 
Qubole developers want to continously test custom features on the master branch to ensure compatibility in future releases.
They created `oss-master` which is a mirror of `master` in prestodb`.
git-patch is used to manage patches and apply them on oss-master to test compatibility.

## Install
    cd ~
    git clone https://github.com/vrajat/git-patch.git
    export PATH=$PATH:~/git-patch/git-patch
    
## Initialize

    git remote add upstream <git url for upstream project>
    git fetch upstream
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
    
## Edit Patches


    # Prepare a feature branch to edit the patch
    git checkout oss-master
    git checkout -b feature_branch
    git fetch upstream
    git rebase upstream/master
    
    #Apply patches
    git patch <section> edit --patch <patch-file>
    
    # Edit patch. 
    # IMPORTANT: All changes should be cached. 
    # IMPORTANT Do not commit any changes. 
    git patch <section> edit --commit
    
    # If all steps are successful, a modified patch is available. 
    # Copy the patch to oss-master and commit it. 
