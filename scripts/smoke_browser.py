"""Verifica o fluxo da interface contra um servidor de desenvolvimento ativo."""

import argparse
import json
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(args.base_url)
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        expect(page.locator("#reaction-a")).to_have_text("36,00kN")
        expect(page.locator("#max-moment")).to_have_text("54,00kN·m")
        expect(page.locator("#max-deflection")).to_have_text("3,24mm")
        assert page.locator("#moment-chart path").count() > 5
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(artifacts / "prototipo-desktop.png"), full_page=True)
        print("OK: cálculo inicial, diagramas e layout desktop")

        page.locator("#uniform-load").fill("0")
        page.locator("#point-load").fill("20")
        expect(page.locator("#feedback")).to_contain_text("Dados alterados")
        expect(page.locator("#export-project")).to_be_disabled()
        expect(page.locator("#print-report")).to_be_disabled()
        page.locator("#calculate").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        expect(page.locator("#reaction-a")).to_have_text("10,00kN")
        expect(page.locator("#max-moment")).to_have_text("30,00kN·m")
        expect(page.locator("#max-deflection")).to_have_text("1,44mm")
        page.locator("#moment-chart").hover()
        expect(page.locator("#moment-reading")).to_contain_text("x =")
        print("OK: alteração de dados, bloqueio de resultados antigos e carga pontual")

        page.locator("#point-position").fill("7")
        page.locator("#calculate").click()
        assert not page.locator("#point-position").evaluate("el => el.validity.valid")
        expect(page.locator("#feedback")).to_contain_text("Dados alterados")
        page.locator("#point-position").fill("3")
        page.locator("#calculate").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")

        with page.expect_download() as download_event:
            page.locator("#export-project").click()
        download = download_event.value
        saved = json.loads(Path(download.path()).read_text())
        assert saved["model"]["point_load_kn"] == 20
        assert saved["model"]["width_m"] == 0.2
        page.locator("#project-file").set_input_files(str(ROOT / "examples/viga-distribuida.json"))
        expect(page.locator("#max-moment")).to_have_text("54,00kN·m")
        expect(page.locator("#uniform-load")).to_have_value("12")
        page.locator("#project-file").set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": b"broken"})
        expect(page.locator("#feedback")).to_contain_text("JSON válido")
        expect(page.locator("#uniform-load")).to_have_value("12")
        page.locator("#reset-example").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        print("OK: validação de posição, exportação e importação de projetos")

        # Uma resposta atrasada não deve substituir dados editados durante o cálculo.
        pending = []
        page.route("**/api/calculate", lambda route: pending.append(route))
        page.locator("#calculate").click()
        expect(page.locator("#calculate")).to_be_disabled()
        page.locator("#uniform-load").fill("15")
        assert len(pending) == 1
        pending[0].continue_()
        expect(page.locator("#feedback")).to_contain_text("Dados alterados durante")
        expect(page.locator("#export-project")).to_be_disabled()
        page.unroute("**/api/calculate")
        page.locator("#reset-example").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        print("OK: resposta atrasada não substitui a edição atual")

        page.emulate_media(media="print")
        assert not page.locator(".parameters").is_visible()
        assert page.locator("#max-moment").is_visible()
        page.pdf(path=str(artifacts / "relatorio-exemplo.pdf"), format="A4", print_background=True, prefer_css_page_size=True)
        page.emulate_media(media="screen")
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator("#deflection-chart")).to_have_attribute("viewBox", "0 0 480 200")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(artifacts / "prototipo-mobile.png"), full_page=True)
        print("OK: impressão/PDF e layout em tela de 390 px")
        browser.close()
    assert not errors, errors
    print("Interface validada sem erros de JavaScript ou de console.")


if __name__ == "__main__":
    main()
