import os
import tarfile
import io

STUB = """#!/bin/bash
# Local Whisper Self-Extracting Installer
# ---------------------------------------
CYAN='\\033[0;36m'
NC='\\033[0m'

echo -e "${CYAN}Preparing Local Whisper Setup...${NC}"

# Create temp dir
TEMP_DIR=$(mktemp -d /tmp/localwhisper_install.XXXXXX)

# Find archive start line
ARCHIVE_START_LINE=$(awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' "$0")

# Extract
tail -n+$ARCHIVE_START_LINE "$0" | tar xz -C "$TEMP_DIR"

# Check extraction
if [ ! -d "$TEMP_DIR/mac_release" ]; then
    echo "Error: Extraction failed."
    exit 1
fi

# Run Installer
cd "$TEMP_DIR/mac_release"
chmod +x install.sh
./install.sh

# Cleanup handled by user choice in installer (usually copying files out), 
# but we can remove the temp installer files if needed. 
# For now, we leave them in tmp to avoid deleting the actual installed app 
# if the user chose to install IN PLACE (which would be in tmp).
# The GUI installer handles copying to a permanent location.

exit 0

__ARCHIVE_BELOW__
"""

def build_installer():
    source_dir = "mac_release"
    output_file = "LocalWhisper_Installer.command"
    
    print(f"Compressing '{source_dir}'...")
    
    # Create Tarball in memory
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir), filter=exclude_venv)
    
    payload = bio.getvalue()
    
    print(f"Payload size: {len(payload)/1024/1024:.2f} MB")
    
    # Write Final File
    with open(output_file, "wb") as f:
        f.write(STUB.encode("utf-8"))
        f.write(payload)
        
    print(f"Created '{output_file}' successfully!")

def exclude_venv(tarinfo):
    if "venv" in tarinfo.name or "__pycache__" in tarinfo.name:
        return None
    return tarinfo

if __name__ == "__main__":
    build_installer()
