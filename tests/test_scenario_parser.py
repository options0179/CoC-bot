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


_CHECKS_HTML = """
<html><body>
<h1 class="c1">1부: 방파제의 초대</h1>
<h2 class="c1">장면 1: 닫힌 관측소</h2>
<h3 class="c1">Keeper</h3>
<p class="c2">창문에 자국이 남아 있습니다. 안에서 소리가 납니다.</p>
<h3 class="c1">Checks</h3>
<table class="c3"><tbody>
<tr><th><p>id</p></th><th><p>skill</p></th><th><p>action</p></th><th><p>success</p></th><th><p>failure</p></th></tr>
<tr><td><p>window-tracks</p></td><td><p>관찰력</p></td><td><p>창틀과 모래를 살핀다.</p></td><td><p>두 번째 발자국을 찾는다.</p></td><td><p>안쪽에서 잡음이 먼저 들린다.</p></td></tr>
<tr><td><p>window-tracks</p></td><td><p>심리학</p></td><td><p>중복 ID</p></td><td><p>성공</p></td><td><p>실패</p></td></tr>
<tr><td><p>blank</p></td><td><p>관찰력</p></td><td><p>빈 결과</p></td><td><p></p></td><td><p>실패</p></td></tr>
<tr><td><p>unknown</p></td><td><p>초능력</p></td><td><p>없는 기능</p></td><td><p>성공</p></td><td><p>실패</p></td></tr>
</tbody></table>
<h3>Keeper 참고</h3><table><tr><th>id</th><th>skill</th><th>action</th><th>success</th><th>failure</th></tr><tr><td>outside</td><td>설득</td><td>표 밖</td><td>성공</td><td>실패</td></tr></table>
<h2>장면 2: 두 번째 기록</h2><h3>Keeper</h3><p>날짜는 내일입니다.</p>
<h3>Checks</h3><table><tr><th>id</th><th>skill</th><th>action</th><th>success</th><th>failure</th></tr><tr><td>record-date</td><td>자료조사</td><td>날짜를 대조한다.</td><td>시간표를 확인한다.</td><td>기록이 뒤섞인다.</td></tr></table>
</body></html>
"""


def test_parse_scenario_html_reads_valid_checks_from_docs_export_table():
    scenes = parse_scenario_html(_CHECKS_HTML)
    assert scenes[0]["lines"] == ["창문에 자국이 남아 있습니다.", "안에서 소리가 납니다."]
    assert scenes[0]["checks"] == [{
        "id": "window-tracks",
        "skill": "관찰력",
        "action": "창틀과 모래를 살핀다.",
        "success": "두 번째 발자국을 찾는다.",
        "failure": "안쪽에서 잡음이 먼저 들린다.",
    }]
    assert scenes[1]["checks"] == [{
        "id": "record-date",
        "skill": "자료조사",
        "action": "날짜를 대조한다.",
        "success": "시간표를 확인한다.",
        "failure": "기록이 뒤섞인다.",
    }]


def test_parse_scenario_html_without_checks_keeps_narration():
    scenes = parse_scenario_html(_SAMPLE_HTML)
    assert scenes[0]["checks"] == []
    assert scenes[1]["checks"] == []


def test_parse_google_docs_export_checks_and_skip_incomplete_or_unsafe_rows():
    # Google Docs exports table cell text inside nested paragraph/span elements.
    html = """
    <html><body>
      <h1 class="title"><span>유리파 관측소</span></h1>
      <h2 class="heading"><span>장면 1: 잠긴 문</span></h2>
      <h3><span>Keeper 낭독</span></h3>
      <p class="narration"><span>문틈으로 희미한 불빛이 샙니다.</span></p>
      <h3><span>Checks</span></h3>
      <table class="docs-table"><tbody>
        <tr>
          <td><p><span>id</span></p></td><td><p><span>skill</span></p></td>
          <td><p><span>action</span></p></td><td><p><span>success</span></p></td>
          <td><p><span>failure</span></p></td>
        </tr>
        <tr>
          <td><p><span>door-listen</span></p></td><td><p><span>관찰력</span></p></td>
          <td><p><span>문 너머를 듣는다.</span></p></td>
          <td><p><span>안쪽에서 숨소리를 듣는다.</span></p></td>
          <td><p><span>바닥이 삐걱여 인기척을 들킨다.</span></p></td>
        </tr>
        <tr>
          <td><p><span></span></p></td><td><p><span>관찰력</span></p></td>
          <td><p><span>id 누락</span></p></td><td><p><span>성공</span></p></td>
          <td><p><span>실패</span></p></td>
        </tr>
        <tr>
          <td><p><span>door-listen</span></p></td><td><p><span>심리학</span></p></td>
          <td><p><span>중복 ID</span></p></td><td><p><span>성공</span></p></td>
          <td><p><span>실패</span></p></td>
        </tr>
        <tr>
          <td><p><span>invalid-skill</span></p></td><td><p><span>초능력</span></p></td>
          <td><p><span>등록되지 않은 기능</span></p></td><td><p><span>성공</span></p></td>
          <td><p><span>실패</span></p></td>
        </tr>
        <tr>
          <td><p><span>short-row</span></p></td><td><p><span>관찰력</span></p></td>
          <td><p><span>결과 셀 누락</span></p></td><td><p><span>성공</span></p></td>
        </tr>
      </tbody></table>
    </body></html>
    """

    scenes = parse_scenario_html(html)

    assert len(scenes) == 1
    assert scenes[0]["lines"] == ["문틈으로 희미한 불빛이 샙니다."]
    assert scenes[0]["checks"] == [{
        "id": "door-listen",
        "skill": "관찰력",
        "action": "문 너머를 듣는다.",
        "success": "안쪽에서 숨소리를 듣는다.",
        "failure": "바닥이 삐걱여 인기척을 들킨다.",
    }]
