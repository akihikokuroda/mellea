#!/bin/bash
# Build script for Mellea API documentation using Sphinx

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="${SCRIPT_DIR}/_build"
SOURCE_DIR="${SCRIPT_DIR}"

echo -e "${GREEN}Building Mellea API Documentation${NC}"
echo "Source directory: ${SOURCE_DIR}"
echo "Build directory: ${BUILD_DIR}"
echo ""

# Check if sphinx-build is available
if ! command -v sphinx-build &> /dev/null; then
    echo -e "${RED}Error: sphinx-build not found${NC}"
    echo "Please install Sphinx and required dependencies:"
    echo "  pip install mellea[docs]"
    echo "or:"
    echo "  pip install sphinx sphinx_rtd_theme sphinx-autodoc-typehints sphinx_mdinclude"
    exit 1
fi

# Parse command line arguments
BUILD_TYPE="html"
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        clean)
            CLEAN=true
            shift
            ;;
        html|dirhtml|singlehtml|text|man|latex|pdf)
            BUILD_TYPE=$1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [clean] [BUILD_TYPE]"
            echo ""
            echo "BUILD_TYPE can be:"
            echo "  html       - Build HTML documentation (default)"
            echo "  dirhtml    - Build HTML with separate directories"
            echo "  singlehtml - Build single HTML file"
            echo "  text       - Build plain text"
            echo "  man        - Build man pages"
            echo "  latex      - Build LaTeX sources"
            echo "  pdf        - Build PDF (requires latex)"
            echo ""
            echo "Options:"
            echo "  clean      - Remove build directory before building"
            echo "  --help, -h - Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Clean build directory if requested
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Cleaning build directory...${NC}"
    rm -rf "${BUILD_DIR}"
    echo "Done."
    echo ""
fi

# Create build directory if it doesn't exist
mkdir -p "${BUILD_DIR}"

# Build documentation
echo -e "${GREEN}Building ${BUILD_TYPE} documentation...${NC}"
sphinx-build -b ${BUILD_TYPE} "${SOURCE_DIR}" "${BUILD_DIR}/${BUILD_TYPE}"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Documentation built successfully!${NC}"
    echo ""
    echo "Output location: ${BUILD_DIR}/${BUILD_TYPE}"
    
    if [ "$BUILD_TYPE" = "html" ] || [ "$BUILD_TYPE" = "dirhtml" ] || [ "$BUILD_TYPE" = "singlehtml" ]; then
        INDEX_FILE="${BUILD_DIR}/${BUILD_TYPE}/index.html"
        if [ -f "$INDEX_FILE" ]; then
            echo "Open in browser: file://${INDEX_FILE}"
            
            # Try to open in browser (macOS)
            if command -v open &> /dev/null; then
                echo ""
                read -p "Open documentation in browser? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    open "${INDEX_FILE}"
                fi
            fi
        fi
    fi
else
    echo -e "${RED}✗ Documentation build failed${NC}"
    exit 1
fi

# Made with Bob
