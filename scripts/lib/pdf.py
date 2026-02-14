#
# PDF Generation: Converts the newsletter HTML to a PDF file.
#
# Tries xhtml2pdf first (pure Python, works everywhere), then weasyprint,
# then pdfkit.  If none is installed the function returns None with a hint.
#

import sys
from pathlib import Path
from typing import Optional


def generate_pdf(html_content: str, output_path: Path) -> Optional[Path]:
    """
    Render *html_content* (a full HTML document) to a PDF at *output_path*.

    Returns the path on success, or ``None`` when no PDF backend is available.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Try xhtml2pdf (pure Python, no system deps) ---
    try:
        from xhtml2pdf import pisa  # type: ignore[import-untyped]

        with open(output_path, "wb") as f:
            result = pisa.CreatePDF(html_content, dest=f)
        if not result.err:
            return output_path
        print("xhtml2pdf reported errors during conversion", file=sys.stderr)
    except ImportError:
        pass
    except Exception as exc:
        print("xhtml2pdf failed: {}".format(exc), file=sys.stderr)

    # --- Try weasyprint (best quality, needs system libs on Windows) ---
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]

        HTML(string=html_content).write_pdf(str(output_path))
        return output_path
    except ImportError:
        pass
    except Exception as exc:
        print("weasyprint failed: {}".format(exc), file=sys.stderr)

    # --- Try pdfkit (needs wkhtmltopdf on PATH) ---
    try:
        import pdfkit  # type: ignore[import-untyped]

        pdfkit.from_string(html_content, str(output_path), options={"quiet": ""})
        return output_path
    except ImportError:
        pass
    except Exception as exc:
        print("pdfkit failed: {}".format(exc), file=sys.stderr)

    # --- No backend available ---
    print(
        "PDF generation skipped — install a backend:\n"
        "  pip install xhtml2pdf           (recommended, pure Python)\n"
        "  pip install weasyprint          (best quality, needs system libs)\n"
        "  pip install pdfkit              (+ wkhtmltopdf on PATH)",
        file=sys.stderr,
    )
    return None
