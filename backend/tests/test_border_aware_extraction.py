from app.services.pdf_layout.cell_extractor import extract_value_cell_right_of_anchor
from app.services.pdf_layout.models import BBox, Word, VerticalLine, HorizontalLine


def test_extract_value_cell_right_of_anchor_uses_vertical_borders():
    # Synthetic row: [PAN]|[ABCDE1234F]|[NEXT]
    words = [
        Word("PAN", BBox(x0=10, top=10, x1=30, bottom=20)),
        Word("ABCDE1234F", BBox(x0=60, top=10, x1=110, bottom=20)),
        Word("NEXT", BBox(x0=130, top=10, x1=160, bottom=20)),
    ]
    v_lines = [
        VerticalLine(x=50, top=5, bottom=25),
        VerticalLine(x=120, top=5, bottom=25),
        VerticalLine(x=170, top=5, bottom=25),
    ]

    res = extract_value_cell_right_of_anchor(
        words=words,
        v_lines=v_lines,
        h_lines=[],
        anchor_idx=0,
    )

    assert res.value == "ABCDE1234F"


def test_extract_value_cell_right_of_anchor_falls_back_without_borders():
    words = [
        Word("LABEL", BBox(x0=10, top=10, x1=40, bottom=20)),
        Word("VALUE", BBox(x0=60, top=10, x1=90, bottom=20)),
    ]

    res = extract_value_cell_right_of_anchor(
        words=words,
        v_lines=[],
        h_lines=[],
        anchor_idx=0,
    )

    assert res.value == "VALUE"
