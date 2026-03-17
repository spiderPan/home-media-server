FROM lscr.io/linuxserver/bazarr:latest

# Install Tesseract and its Python wrappers
RUN apk add --no-cache tesseract-ocr tesseract-ocr-data-eng && \
    pip install pytesseract Pillow --break-system-packages