"""Worker OCR local isolado para permitir timeout do Tesseract nativo."""
import argparse

import pymupdf as fitz


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--page', required=True, type=int)
    parser.add_argument('--language', required=True)
    parser.add_argument('--tessdata', required=True)
    parser.add_argument('--bbox', nargs=4, type=float)
    args = parser.parse_args()
    with fitz.open(args.pdf) as doc:
        pixmap = doc[args.page - 1].get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(args.bbox) if args.bbox else None)
        pixmap.set_dpi(288, 288)
        with fitz.open('pdf', pixmap.pdfocr_tobytes(language=args.language, tessdata=args.tessdata)) as recognized:
            print(recognized[0].get_text().strip())


if __name__ == '__main__':
    main()
