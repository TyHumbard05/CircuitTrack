param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

git init
git add .
git commit -m "Initial CircuitTrack deployment"
git branch -M main
git remote remove origin 2>$null
git remote add origin $RepoUrl
git push -u origin main
