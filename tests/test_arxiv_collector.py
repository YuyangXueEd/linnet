from extensions.arxiv.collector import (
    _normalise_caption_math,
    _parse_first_figure,
    fetch_papers,
    keyword_match,
)


def test_keyword_match_positive():
    text = "A foundation model for medical image segmentation using MRI and CT scans"
    must_include = ["medical image", "MRI", "CT scan", "segmentation"]
    assert keyword_match(text, must_include) is True


def test_keyword_match_negative():
    text = "A graph neural network for protein folding prediction"
    must_include = ["medical image", "MRI", "CT scan", "segmentation"]
    assert keyword_match(text, must_include) is False


def test_keyword_match_case_insensitive():
    text = "MEDICAL IMAGING with Diffusion Models"
    must_include = ["medical imaging"]
    assert keyword_match(text, must_include) is True


def test_fetch_papers_returns_list():
    """fetch_papers with zero max_results returns empty list without hitting network."""
    results = fetch_papers(categories=["cs.CV"], must_include=["medical"], max_results=0)
    assert isinstance(results, list)


def test_parse_first_figure_extracts_url_and_caption():
    html = """
        <section>
            <figure id="S3.F1" class="ltx_figure">
                <img src="2604.12345v1/Figures/figure1.png" alt="Refer to caption">
                <figcaption class="ltx_caption ltx_centering"><span class="ltx_tag ltx_tag_figure">Figure 1: </span>A test architecture overview.</figcaption>
            </figure>
        </section>
        """

    figure = _parse_first_figure(html, "https://arxiv.org/html/2604.12345")

    assert figure == {
        "figure_url": "https://arxiv.org/html/2604.12345v1/Figures/figure1.png",
        "figure_caption": "A test architecture overview.",
    }


def test_normalise_caption_math_wraps_latex_for_katex():
    caption = (
        "Illustration of PR-MaGIC updating the embedding vector distribution "
        "ρ t \\rho_{t} toward μ \\mu."
    )

    normalised = _normalise_caption_math(caption)

    assert "ρ t \\rho_{t}" not in normalised
    assert "\\( \\rho_{t} \\)" in normalised
    assert "\\( \\mu \\)" in normalised
