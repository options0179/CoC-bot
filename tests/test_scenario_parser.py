from scenario_parser import parse_scenario_html, split_sentences


def test_split_sentences_splits_on_terminators():
    assert split_sentences("늦은 오후입니다. 하루는 특별하지 않았습니다.") == [
        "늦은 오후입니다.",
        "하루는 특별하지 않았습니다.",
    ]


def test_split_sentences_keeps_bracketed_dialogue_intact():
    text = "「일 끝났어요? 저는 조금 일찍 나왔어요.」"
    assert split_sentences(text) == [text]


def test_split_sentences_ignores_blank_input():
    assert split_sentences("   ") == []


_SAMPLE_HTML = """
<html><body>
<h1 class="c1">제1부 &#8212; 평범한 하루의 끝</h1>
<h2 class="c1">장면 1. 일상</h2>
<h3 class="c1">Keeper 상황 묘사</h3>
<p class="c2">늦은 오후입니다. 하루는 특별하지 않았습니다.</p>
<p class="c2">「일 끝났어요? 저는 조금 일찍 나왔어요.」</p>
<h3 class="c1">PC 행동</h3>
<p class="c2">이 문단은 낭독 대상이 아니다.</p>
<h2 class="c1">장면 2. 저녁 식사</h2>
<h3 class="c1">Keeper 낭독</h3>
<p class="c2">저녁 식사 시간입니다.</p>
<h2 class="c1">장면 3. 최종 선택</h2>
<h3 class="c1">판정</h3>
<p class="c2">이 장면에는 Keeper 낭독이 없다.</p>
</body></html>
"""


def test_parse_scenario_html_extracts_only_keeper_sections():
    scenes = parse_scenario_html(_SAMPLE_HTML)
    assert [s["scene"] for s in scenes] == ["장면 1. 일상", "장면 2. 저녁 식사"]
    assert scenes[0]["part"] == "제1부 — 평범한 하루의 끝"
    assert scenes[0]["lines"] == [
        "늦은 오후입니다.",
        "하루는 특별하지 않았습니다.",
        "「일 끝났어요? 저는 조금 일찍 나왔어요.」",
    ]
    assert scenes[1]["lines"] == ["저녁 식사 시간입니다."]


def test_parse_scenario_html_drops_scenes_without_narration():
    scenes = parse_scenario_html(_SAMPLE_HTML)
    assert "장면 3. 최종 선택" not in [s["scene"] for s in scenes]
