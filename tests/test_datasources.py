"""Testes da leitura compartilhada da base de produção."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import pandas as pd

from utils import _datasources as fontes
from utils import _home_data


def _workbook_prod_gpon() -> bytes:
    prod = pd.DataFrame(
        {
            "OS": ["A1", "A2"],
            "Data Agendamento": ["2026-11-02", "2026-11-03"],
            "Matrícula": ["Z700478", "Z700478"],
            "Nome Equipe": ["TECNICO TESTE", "TECNICO TESTE"],
            "Pontos": [2.5, 3.0],
        }
    )
    gpon = pd.DataFrame(
        {
            "Contrato": ["C1", "C1", "C2"],
            "Data Agendamento": ["2026-11-03", "2026-11-03", "2026-11-04"],
            "Matrícula": ["Z700478", "Z700478", "Z700478"],
            "Nome Equipe": ["TECNICO TESTE"] * 3,
            "Pontos": [1.5, 99.0, 2.0],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        prod.to_excel(writer, sheet_name="Prod", index=False)
        gpon.to_excel(writer, sheet_name="gpon", index=False)
    return buffer.getvalue()


class TestBaseProducao(unittest.TestCase):
    def setUp(self) -> None:
        fontes._baixar_url.clear()
        fontes._baixar_autenticado.clear()
        fontes._carregar_base_producao.clear()
        _home_data._carregar_producao.clear()

    def test_ignora_html_e_usa_workbook_com_abas_em_qualquer_caixa(self) -> None:
        conteudo = _workbook_prod_gpon()

        class Resposta:
            status_code = 200
            content = b"<!DOCTYPE html><html>login</html>" + b"x" * 200

        fontes._baixar_url.clear()
        with patch("utils._datasources.requests.get", return_value=Resposta()):
            self.assertIsNone(fontes.baixar_url("https://exemplo.test/planilha"))

        def baixador(_file_id: str, destino: str) -> bytes | None:
            return conteudo if destino == "xlsx" else None

        df = fontes.carregar_base_producao("id-teste", baixador=baixador)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 4)  # Gpon remove 1 contrato duplicado.
        self.assertEqual(set(df["__origem__"]), {"Prod", "Gpon"})
        self.assertIn("ORIGEM", df.columns)
        self.assertEqual(float(df["Pontos"].sum()), 9.0)

    def test_home_reusa_baixador_e_mesmo_parser(self) -> None:
        conteudo = _workbook_prod_gpon()
        with patch.object(
            _home_data, "_baixar_arquivo", return_value=conteudo
        ) as baixar:
            df = _home_data._carregar_producao()
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 4)
        baixar.assert_called()

    def test_resumo_filtra_tecnico_e_separa_prod_gpon(self) -> None:
        df = pd.DataFrame(
            {
                "Data Agendamento": [
                    "2026-11-02",
                    "2026-11-03",
                    "2026-11-04",
                    "2026-11-05",
                    "2026-10-30",
                ],
                "Pontos": [2.5, 1.5, 4.0, 10.0, 99.0],
                "Matrícula": ["Z700478", "Z700478", "OUTRO", "OUTRO", "Z700478"],
                "Nome Equipe": ["TECNICO TESTE"] * 5,
                "ORIGEM": ["Prod", "Gpon", "Prod", "Gpon", "Prod"],
            }
        )
        with patch.object(_home_data, "_carregar_producao", return_value=df):
            resumo = _home_data.resumo_producao(
                "TECNICO TESTE", "Z700478", "USER.TESTE", False
            )

        self.assertTrue(resumo["ok"])
        self.assertEqual(resumo["os"], 2)
        self.assertAlmostEqual(resumo["pontos"], 4.0)
        self.assertAlmostEqual(resumo["pontos_prod"], 2.5)
        self.assertAlmostEqual(resumo["pontos_gpon"], 1.5)
        self.assertAlmostEqual(resumo["media_os"], 2.0)
        self.assertGreater(resumo["projecao"], 4.0)
        self.assertEqual(resumo["data_ref"].isoformat(), "2026-11-05")

    def test_resumo_sem_fonte_devolve_aviso(self) -> None:
        with patch.object(
            _home_data, "_carregar_producao", return_value=pd.DataFrame()
        ):
            resumo = _home_data.resumo_producao("TECNICO", "LOGIN", "USER")
        self.assertFalse(resumo["ok"])
        self.assertIn("indisponível", resumo["motivo"])


if __name__ == "__main__":
    unittest.main()
