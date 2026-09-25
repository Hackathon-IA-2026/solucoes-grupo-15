"""Tests for the post-CAPTCHA SEI browser automation prototype."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))

import automated_batch_downloader as downloader


class SearchExtractionTests(unittest.TestCase):
    def test_uses_first_processes_in_result_order(self) -> None:
        page = (MODULE_DIR / "samples" / "sei-results-august-05.md").read_text(
            encoding="utf-8"
        )

        hits = downloader.extract_process_hits(
            page,
            "https://sei.aneel.gov.br/sei/resultados",
        )

        self.assertEqual(
            [hit.process_number for hit in downloader.select_hits(hits, 3)],
            [
                "48500.027542/2026-62",
                "48500.004024/2017-80",
                "48500.000639/2019-07",
            ],
        )

    def test_resolves_process_link_against_official_page(self) -> None:
        page = '<a href="detalhe?id=42">48500.027542/2026-62</a>'

        hits = downloader.extract_process_hits(
            page,
            "https://sei.aneel.gov.br/sei/modulos/pesquisa/resultados.php",
        )

        self.assertEqual(
            hits[0].href,
            "https://sei.aneel.gov.br/sei/modulos/pesquisa/detalhe?id=42",
        )


class SearchFieldTests(unittest.TestCase):
    def test_type_process_theme_uses_official_select_and_dates(self) -> None:
        values = downloader.search_field_values(
            theme="Fiscalização da Distribuição: Processo Administrativo Sancionador",
            theme_field="tipo-processo",
            date_from="05/08/2026",
            date_to="05/08/2026",
        )

        self.assertEqual(
            values,
            {
                "select_label": "Fiscalização da Distribuição: Processo Administrativo Sancionador",
                "free_text": None,
                "date_from": "05/08/2026",
                "date_to": "05/08/2026",
            },
        )


class ProcessFamilyTests(unittest.TestCase):
    def test_groups_public_documents_under_one_process_family(self) -> None:
        manifest = downloader.process_manifest(
            {
                "header": {"Processo": "48500.027542/2026-62", "Tipo": "Outorga"},
                "rows": [
                    {
                        "sei": "0461692",
                        "type": "Carta 542",
                        "date": "18/08/2026",
                        "inclusionDate": "20/09/2026",
                        "unit": "PROTOCOLO-GERAL",
                        "href": "https://sei.aneel.gov.br/documento/461692",
                        "relatedProcess": False,
                    },
                    {
                        "sei": "0461693",
                        "type": "Carta",
                        "date": "20/09/2026",
                        "inclusionDate": "20/09/2026",
                        "unit": "PROTOCOLO-GERAL",
                        "href": "",
                        "relatedProcess": False,
                    },
                ],
            },
            downloader.ProcessHit("48500.027542/2026-62"),
            "sei",
        )

        self.assertEqual(manifest["process_number"], "48500.027542/2026-62")
        self.assertEqual(len(manifest["documents"]), 2)
        self.assertEqual(
            {document["family_id"] for document in manifest["documents"]},
            {"sei-process-48500-027542-2026-62"},
        )
        self.assertEqual(manifest["documents"][0]["version_date"], "2026-08-18")
        self.assertEqual(manifest["documents"][1]["locator"], "missing://sei/0461693")


if __name__ == "__main__":
    unittest.main()
