#!/bin/bash

set -e  # Stop on any error

PACKAGE_NAME="ytml-toolkit"  # Change this to your package name
VERSION_BUMP_TYPE="patch"    # Change to "patch" if you want a patch update
CLI_FILE="ytml/cli.py"       # Path to CLI file containing VERSION variable

echo "🚀 Deploying $PACKAGE_NAME..."

# Step 1: Remove old builds
echo "🗑️  Removing old distributions..."
rm -rf dist/*

# Step 2: Get current version from setup.py
echo "🔍 Fetching current version..."
CURRENT_VERSION=$(grep -oE 'version="[0-9]+\.[0-9]+\.[0-9]+"' setup.py | cut -d '"' -f2)
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Step 3: Increment version
if [ "$VERSION_BUMP_TYPE" == "minor" ]; then
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
elif [ "$VERSION_BUMP_TYPE" == "patch" ]; then
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
else
    echo "❌ Invalid version bump type: $VERSION_BUMP_TYPE"
    exit 1
fi

echo "✅ Updating version: $CURRENT_VERSION → $NEW_VERSION"

# Step 4: Update version in setup.py
sed -i.bak "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/g" setup.py
rm setup.py.bak  # Cleanup backup file

# Step 5: Update version in CLI script
sed -i.bak "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/g" "$CLI_FILE"
rm "$CLI_FILE.bak"  # Cleanup backup file

echo "🔄 Updated versions in setup.py and $CLI_FILE"

# Step 6: Build package
echo "🛠️  Building package..."
python -m build

# Step 7: Publish package
echo "🚀 Publishing package to PyPI..."
python -m twine upload dist/*

# Step 8: Commit and tag the new version in Git
git add setup.py "$CLI_FILE"
git commit -m "Bump version to $NEW_VERSION"
git tag "v$NEW_VERSION"
git push origin main --tags

echo "✅ Git version updated and pushed."

# Step 9: Success message
echo "🎉 Deployment complete! Version $NEW_VERSION is now live on PyPI."
