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
            args=["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(args.base_url)
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        expect(page.locator("#reaction-a")).to_have_text("36,00kN")
        expect(page.locator("#max-moment")).to_have_text("54,00kN·m")
        expect(page.locator("#max-deflection")).to_have_text("3,24mm")
        expect(page.locator("#bending-stress")).to_have_text("6,48MPa")
        expect(page.locator("#shear-stress")).to_have_text("0,54MPa")
        expect(page.locator("#rotation-a")).to_have_text("1,728 mrad")
        expect(page.locator("#rotation-b")).to_have_text("-1,728 mrad")
        expect(page.locator("#beam-3d")).to_have_attribute("data-ready", "true", timeout=15000)
        expect(page.locator("#validation-status")).to_contain_text("10/10 casos")
        expect(page.locator("#validation-status")).to_contain_text("90/90 comparações")
        assert page.locator("#moment-chart path").count() > 5
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(artifacts / "prototipo-3d-desktop.png"), full_page=True)
        page.locator(".model-views").screenshot(path=str(artifacts / "modelos-2d-3d.png"))
        print("OK: cálculo inicial, novos resultados, 90 comparações e layout desktop")

        canvas = page.locator("#beam-3d canvas")
        initial_view = canvas.screenshot()
        canvas.press("ArrowLeft")
        assert canvas.screenshot() != initial_view, 'Rotação deve mudar a imagem renderizada'
        rotated_view = canvas.screenshot()
        page.locator("#zoom-in").click()
        assert canvas.screenshot() != rotated_view, 'Zoom deve mudar o enquadramento'
        page.locator("#reset-camera").click()
        page.locator("#show-deformed").check()
        expect(page.locator("#beam-3d")).to_have_attribute("data-deformed", "true")
        expect(page.locator("#scene-status")).to_contain_text("Deformada ×")
        assert canvas.screenshot() != initial_view, 'A deformada deve mudar a geometria visível'
        page.screenshot(path=str(artifacts / "prototipo-3d-deformada.png"), full_page=True)
        page.locator(".model-views").screenshot(path=str(artifacts / "modelos-deformada.png"))
        page.locator("#show-deformed").uncheck()
        expect(page.locator("#beam-3d")).to_have_attribute("data-deformed", "false")
        print("OK: renderização 3D, rotação por teclado, zoom e deformada com escala indicada")

        page.locator("[data-case-id=combined]").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        expect(page.locator("#max-moment")).to_have_text("74,67kN·m")
        expect(page.locator("#bending-stress")).to_have_text("8,96MPa")
        expect(page.locator("#point-position")).to_have_value("2")
        with page.expect_download() as validation_download:
            page.locator("#download-validation").click()
        report = json.loads(Path(validation_download.value.path()).read_text())
        assert report['passed_checks'] == report['total_checks'] == 90
        page.locator("[data-case-id=shorter]").click()
        expect(page.locator("#feedback")).to_contain_text("Análise concluída")
        expect(page.locator("#beam-3d")).to_have_attribute("data-span", "4.5")
        expect(page.locator("#beam-3d")).to_have_attribute("data-width", "0.15")
        expect(page.locator("#beam-3d")).to_have_attribute("data-height", "0.4")
        expect(page.locator("#width")).to_have_value("15")
        expect(page.locator("#max-moment")).to_have_text("30,01kN·m")
        page.locator("#reset-example").click()
        expect(page.locator("#max-moment")).to_have_text("54,00kN·m")
        print("OK: carregar caso de referência e baixar a conferência completa")

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
        expect(page.locator(".scene-print-image")).to_be_visible()
        expect(page.locator("#beam-3d canvas")).not_to_be_visible()
        page.wait_for_function("document.querySelector('.scene-print-image').naturalWidth > 100")
        page.pdf(path=str(artifacts / "relatorio-3d-exemplo.pdf"), format="A4", print_background=True, prefer_css_page_size=True)
        page.emulate_media(media="screen")
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator("#deflection-chart")).to_have_attribute("viewBox", "0 0 480 200")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        expect(page.locator("#beam-3d canvas")).to_be_visible()
        page.screenshot(path=str(artifacts / "prototipo-3d-mobile.png"), full_page=True)
        print("OK: impressão/PDF e layout em tela de 390 px")

        fallback = browser.new_page()
        fallback.add_init_script("""const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                return type.startsWith('webgl') ? null : getContext.call(this, type, ...args);
            };""")
        fallback.goto(args.base_url)
        expect(fallback.locator("#feedback")).to_contain_text("Análise concluída")
        expect(fallback.locator("#scene-status")).to_contain_text("3D indisponível")
        expect(fallback.locator("#max-moment")).to_have_text("54,00kN·m")
        fallback.close()
        print("OK: cálculo e esquema 2D disponíveis mesmo sem WebGL")
        browser.close()
    assert not errors, errors
    print("Interface validada sem erros de JavaScript ou de console.")


if __name__ == "__main__":
    main()
