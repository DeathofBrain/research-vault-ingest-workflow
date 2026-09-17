#!/usr/bin/env python3
"""ResearchVault ingest 校验器（只读，不修改任何内容）。

用法：
  python3 tools/validate_ingest.py            # 校验默认目标（最近一次 ingest 的 Note 与全部 Knowledge 页）
  python3 tools/validate_ingest.py --note <note.md> --pdf <file.pdf>

退出码 0 表示全部必须项通过；非 0 表示存在 FAIL。报告写入 01knowledge/.meta/validation_report.json。
"""
import argparse, datetime, glob, json, os, re, subprocess, sys, yaml

ROOT = os.path.abspath(os.path.expanduser(os.environ.get("RESEARCH_VAULT_ROOT", os.path.join(os.path.dirname(__file__), ".."))))
KNOW = os.path.join(ROOT, "01knowledge")
TYPES = {"knowledge-theme", "knowledge-concept", "knowledge-method",
         "knowledge-relation", "knowledge-controversy", "knowledge-synthesis"}
PAGE_KEYS = {"type", "title", "aliases", "status", "evidence_count", "source_notes",
             "related", "last_updated", "evidence_status"}
REL_EXTRA = {"subject", "relation", "object", "agreement"}
STATUS = {"emerging", "developing", "established", "conditional", "contested"}
EVID = {"fulltext_verified", "note_supported", "interpretation", "mixed"}
ROLES = {"直接证据", "机制证据", "情境证据", "条件证据", "相关证据"}
VERIF = {"fulltext_verified", "note_supported", "interpretation"}
PROV = {"Evidence-backed Gap", "Interpretive Gap"}
H2 = ["概述与边界", "证据总览", "研究发现", "研究空白", "使用与边界" , "来源与边界"]

RESULTS = []
def check(name, ok, detail="", level="FAIL"):
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS  " if ok else "FAIL  ") + name + ((" :: " + detail) if detail else ""))
    return ok
def warn(name, ok, detail=""):
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail, "level": "WARN"})
    print(("PASS  " if ok else "WARN  ") + name + ((" :: " + detail) if detail else ""))

def is_analytical_note(fm):
    return bool(fm) and (fm.get("type") == "literature-note" or
                         "literature-note" in (fm.get("tags") or []))


def read(p):
    return open(p, encoding="utf-8").read()
def fm_of(text):
    if not text.startswith("---\n"):
        return None, text
    body = text.split("\n---\n", 1)
    if len(body) < 2:
        return None, text
    return yaml.safe_load(body[0][4:]), body[1]

PATH_TOKEN = re.compile(r"(?:03fulltext|02vault|01knowledge|\u8bba\u6587\u5e93|storage|_index)/[^\s|\uff0c\u3002\uff1b\uff09\]]*")
def key_like_tokens(text):
    """Opaque Zotero/PDF-style keys: 8 chars of [0-9A-Z] mixing letters and digits.
    Path tokens are masked first because a fulltext filename legitimately carries the key."""
    masked = PATH_TOKEN.sub("<path>", text)
    return {t for t in re.findall(r"\b[0-9A-Z]{8}\b", masked)
            if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)}

def structural_pipes(line):
    """Count only cell-separating pipes: wikilink aliases ([[a|b]] or [[a\\|b]]) are not separators."""
    return re.sub(r"\[\[[^\]]*\]\]", "X", line).count("|")

def index_targets(idx_text):
    """Link targets inside 01knowledge/index.md, normalized so 'x/y' and 'x/y.md' compare equal."""
    out = set()
    for t, _ in wikilinks(idx_text):
        t = t.strip().lstrip("/")
        out.add(t)
        out.add(t + ".md" if not t.endswith(".md") else t[:-3])
    return out

MD_FILES = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".git", ".obsidian", "node_modules"}]
    for f in filenames:
        if f.endswith(".md"):
            MD_FILES.append(os.path.join(dirpath, f))

def resolve_link(target):
    """Resolve an Obsidian-style link target to a real file in the vault."""
    t = target.strip().lstrip("/")
    cands = [t, t + ".md", os.path.join(ROOT, t), os.path.join(ROOT, t + ".md")]
    for c in cands:
        if os.path.isfile(c):
            return c
    tails = [c for c in MD_FILES if c.endswith("/" + t) or c.endswith("/" + t + ".md")]
    return tails[0] if len(tails) >= 1 else None

def wikilinks(text):
    r"""Return (target, alias) for every [[link]] / [[link\|alias]] occurrence."""
    out = []
    for m in re.finditer(r"\[\[([^\]\n]+?)\]\]", text):
        parts = re.split(r"\\?\|", m.group(1))
        out.append((parts[0].strip(), "|".join(parts[1:]).strip()))
    return out

# ---------------- Note 校验 ----------------
LEGACY_NOTE_HEADINGS = (
    "## 基本信息",
    "## 一句话摘要",
    "## 组会讲论文（导师六问框架）",
    "## 研究对象",
    "## 研究方法",
    "### 方法概述",
    "### 方法分析",
    "## 技术机制与设计权衡",
    "## 数据来源",
    "## 研究结论",
    "## 关联精读笔记",
    "## 我的判断",
)


def note_headings(text, max_level=3):
    pattern = r"^#{1,%d} .*$" % max_level
    return [m.group(0).rstrip() for m in re.finditer(pattern, text, flags=re.M)
            if m.group(0).strip() != "# {{title}}"]


def validate_template_sections(raw, fm, template):
    version = str(fm.get("template_version", 1))
    if version not in {"1", "2"}:
        detail = "unsupported template_version:" + version
        check("note.template.sections", False, detail)
        check("note.template.section_order", False, detail)
        return
    # Unversioned notes keep their original structure when the live template evolves.
    max_level = 3 if version == "1" else 4
    want = list(LEGACY_NOTE_HEADINGS) if version == "1" else note_headings(template, max_level)
    got = note_headings(raw, max_level)
    missing = [h for h in want if h not in got]
    check("note.template.sections", not missing, "missing:" + ";".join(missing))
    order_ok = [h for h in got if h in want] == [h for h in want if h in got]
    check("note.template.section_order", order_ok, " -> ".join(got))


def validate_note(note_path, pdf_path):
    raw = read(note_path)
    fm, body = fm_of(raw)
    req = ["title", "type", "zotero_key", "pdf_key", "collection", "note_path", "fulltext_path",
           "theme", "study_area", "data_source", "methodology", "core_variable", "key_finding", "relevance"]
    check("note.frontmatter.parses", fm is not None)
    if fm is None:
        return
    check("note.frontmatter.required", all(k in fm and fm[k] not in (None, "") for k in req),
          ",".join(k for k in req if k not in fm))
    check("note.type", fm.get("type") == "literature-note", str(fm.get("type")))
    check("note.no_placeholders", not re.findall(r"\{\{[^}]*\}\}", raw))
    for k in ("note_path", "fulltext_path"):
        rel = fm[k]
        p = os.path.join(ROOT, "02vault", rel) if k == "note_path" else os.path.join(ROOT, rel)
        check("note.path_resolves." + k, os.path.isfile(p), p)
    check("note.self_path_consistent",
          os.path.abspath(note_path) == os.path.abspath(os.path.join(ROOT, "02vault", fm["note_path"])),
          fm["note_path"])
    ft = os.path.join(ROOT, fm["fulltext_path"])
    check("note.frontmatter.fulltext_path.exists", os.path.isfile(ft), ft)
    tpl = read(os.path.join(ROOT, "模板/论文精读模板.md"))
    validate_template_sections(raw, fm, tpl)
    # links
    bad = [t for t, _ in wikilinks(raw) if not resolve_link(t)]
    check("note.links.resolve", not bad, ";".join(bad))
    # images in fulltext
    ftxt = read(ft)
    imgs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", ftxt)
    miss = []
    for i in imgs:
        if i.startswith("http"):
            continue
        p = os.path.normpath(os.path.join(os.path.dirname(ft), i))
        if not os.path.isfile(p):
            miss.append(i)
    check("fulltext.images_resolved", not miss, "missing:" + ",".join(miss))
    check("fulltext.non_empty", len(ftxt) > 500, "chars=%d" % len(ftxt))
    # quotes vs PDF
    if pdf_path and os.path.isfile(pdf_path):
        ok, detail = verify_quotes(raw, pdf_path)
        check("note.quotes.verified_in_pdf", ok, detail)
    return fm

DROP = set(" \t\n\r\u00ad\u2018\u2019\u201c\u201d\"'-\u2014\u2013`\u2212")
def hard(s):
    return "".join(c for c in s if c not in DROP)

def verify_quotes(note_text, pdf_path):
    try:
        from pypdf import PdfReader
    except Exception as e:
        return None, "pypdf unavailable: %s" % e
    r = PdfReader(pdf_path)
    pages = [hard(p.extract_text() or "") for p in r.pages]
    qlines = [l for l in note_text.split("\n") if l.startswith("> \u201c")]
    bad = []
    for l in qlines:
        m = re.match(r'>\s*\u201c(.*)\u201d\s*\u2014\s*PDF\s*\u7b2c\s*([\d\u2013\-, ]+)\s*\u9875', l)
        if not m:
            bad.append("unparsed:" + l[:40]); continue
        stated = [int(x) for x in re.findall(r"\d+", m.group(2))]
        # Elision-aware: a quote may contain "…" / "..." to mark omitted text.
        # Every fragment (>=15 chars after normalization) must be locatable on a
        # stated page, either whole or split across two stated pages.
        frags = [f for f in re.split("\u2026|\\.\\.\\.", m.group(1)) if len(hard(f)) >= 15] or [m.group(1)]
        for fr in frags:
            h = hard(fr)
            if set(hits_pages(pages, h)) & set(stated):
                continue
            if spans_ok(pages, h, stated):
                continue
            bad.append(m.group(1)[:50] + " [frag:" + fr.strip()[:30] + "]")
            break
    return (not bad), "%d/%d quotes verified; bad=%s" % (len(qlines) - len(bad), len(qlines), ";".join(bad))

def hits_pages(pages, h):
    return [i + 1 for i, t in enumerate(pages) if h in t]

def spans_ok(pages, h, stated):
    if len(stated) < 2:
        return False
    for a in range(len(pages)):
        for b in range(a + 1, len(pages)):
            if b + 1 not in stated or a + 1 not in stated:
                continue
            for s in range(20, len(h) - 20):
                if h[:s] in pages[a] and h[s:] in pages[b]:
                    return True
    return False

# ---------------- Knowledge 校验 ----------------
def knowledge_pages():
    out = []
    for p in glob.glob(os.path.join(KNOW, "**", "*.md"), recursive=True):
        rel = os.path.relpath(p, ROOT)
        if "/.meta/" in "/" + rel:
            continue
        fm, _ = fm_of(read(p))
        if fm and fm.get("type") in TYPES:
            out.append((p, fm))
    return out

def validate_knowledge():
    pages = knowledge_pages()
    check("knowledge.pages_discovered", len(pages) >= 1, "%d page(s)" % len(pages))
    idx = read(os.path.join(KNOW, "index.md"))
    linked = index_targets(idx)
    allside = sorted(glob.glob(os.path.join(KNOW, ".meta/claims/*.json"))) + \
              sorted(glob.glob(os.path.join(KNOW, ".meta/gaps/*.json")))
    for p, fm in pages:
        rel = os.path.relpath(p, ROOT)
        text = read(p)
        body = fm_of(text)[1]
        slug = None
        check("kp.schema.keys." + rel, set(fm) == PAGE_KEYS or (fm["type"] == "knowledge-relation" and set(fm) == PAGE_KEYS | REL_EXTRA),
              "extra/missing:" + ",".join(sorted(set(fm) ^ PAGE_KEYS)))
        check("kp.schema.type." + rel, fm.get("type") in TYPES, str(fm.get("type")))
        check("kp.schema.status." + rel, fm.get("status") in STATUS, str(fm.get("status")))
        check("kp.schema.evidence_status." + rel, fm.get("evidence_status") in EVID, str(fm.get("evidence_status")))
        check("kp.schema.last_updated." + rel, bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(fm.get("last_updated")))), str(fm.get("last_updated")))
        # source notes
        srcs = []
        for s in fm.get("source_notes") or []:
            for t, _ in wikilinks(s) or [(s.strip("[]|"), "")]:
                srcs.append(t)
        resolved, ghosts = [], []
        for t in srcs:
            r = resolve_link(t)
            if r is None:
                ghosts.append(t)
            else:
                nf = fm_of(read(r))[0] or {}
                if not is_analytical_note(nf):
                    ghosts.append(t + " (not an Analytical Note)")
                else:
                    resolved.append(r)
        check("kp.source_notes.real_analytical_notes." + rel, not ghosts, ";".join(ghosts))
        check("kp.source_notes.distinct", len(set(resolved)) == len(resolved))
        check("kp.evidence_count.matches." + rel, fm.get("evidence_count") == len(set(resolved)),
              "declared=%s actual=%s" % (fm.get("evidence_count"), len(set(resolved))))
        # template structure
        for h in [x for x in H2 if x != "使用与边界"]:
            check("kp.template.section." + rel + "." + h, ("## " + h) in body)
        h2s = [m.group(1).strip() for m in re.finditer(r"^## (.+)$", body, flags=re.M)]
        seq = [h for h in ["概述与边界", "证据总览", "研究发现", "研究空白", "使用与启示", "来源与边界"]]
        check("kp.template.order." + rel, [h for h in h2s if h in seq] == seq, " -> ".join(h2s))
        check("kp.template.summary_callout." + rel, "> [!summary]" in body)
        check("kp.template.evidence_table." + rel,
              "| 论文 | 证据角色 | 验证状态 | 链接 |" in body)
        # no raw keys / no machine metadata in prose
        keys = key_like_tokens(body)
        check("kp.no_raw_keys_in_prose." + rel, not keys, ";".join(sorted(keys)))
        check("kp.no_html_comments." + rel, "<!--" not in body)
        check("kp.no_claim_ids_visible." + rel, not re.search(r"\b(claim|gap)-[a-z0-9-]*\d{3}\b", body))
        # links
        bad = [t for t, _ in wikilinks(body) if not resolve_link(t)]
        check("kp.links.resolve." + rel, not bad, ";".join(bad))
        # claims 1:1
        heads = [m.group(1).strip() for m in re.finditer(r"^### (.+)$", body, flags=re.M) if m.group(1).startswith("结论")]
        sidecars = []
        for sp in sorted(glob.glob(os.path.join(KNOW, ".meta/claims/*.json"))):
            d = json.load(open(sp, encoding="utf-8"))
            if os.path.relpath(p, ROOT).endswith(d.get("page", "").split("/", 1)[-1]) or d.get("page") == rel:
                sidecars.append((sp, d))
        ids = [d["claim_id"] for _, d in sidecars]
        check("kp.claims.ids_format." + rel, all(re.match(r"^claim-[a-z0-9-]+-\d{3}$", i) for i in ids), ";".join(ids[:3]))
        check("kp.claims.1to1." + rel, len(heads) == len(sidecars) > 0,
              "page=%d sidecars=%d" % (len(heads), len(sidecars)))
        matched = sum(1 for (sp, d), h in zip(sorted(sidecars, key=lambda x: x[1]["claim_id"]), heads)
                      if hard(d["heading"]) == hard(h))
        check("kp.claims.heading_match." + rel, matched == len(sidecars), "%d/%d" % (matched, len(sidecars)))
        for sp, d in sidecars:
            cid = d.get("claim_id", "?")
            ok_e = True; det = []
            for e in d.get("evidence", []):
                if e.get("evidence_role") not in ROLES:
                    ok_e = False; det.append("role:" + str(e.get("evidence_role")))
                if e.get("verification_state") not in VERIF:
                    ok_e = False; det.append("verif:" + str(e.get("verification_state")))
                if not resolve_link(e.get("source_note", "")):
                    ok_e = False; det.append("ghost:" + str(e.get("source_note")))
                if e.get("verification_state") == "fulltext_verified" and not os.path.isfile(os.path.join(ROOT, e.get("fulltext_path", ""))):
                    ok_e = False; det.append("no fulltext for fulltext_verified")
            check("meta.claim.schema." + cid, ok_e and set(d) >= {"claim_id", "page", "heading", "statement",
                  "conditions", "mechanism", "limitations", "evidence", "last_updated"}, ";".join(det))
        # gaps
        gs = []
        for gp in sorted(glob.glob(os.path.join(KNOW, ".meta/gaps/*.json"))):
            d = json.load(open(gp, encoding="utf-8"))
            if d.get("page") == rel:
                gs.append((gp, d))
        check("kp.gaps.present." + rel, len(gs) > 0, "%d gap sidecars" % len(gs))
        for gp, d in gs:
            okg = d.get("gap_provenance") in PROV and d.get("verification_state") in VERIF and \
                  bool(re.match(r"^gap-[a-z0-9-]+-\d{3}$", d.get("gap_id", ""))) and \
                  all(resolve_link(x) for x in d.get("source_notes", []))
            if d.get("gap_provenance") == "Interpretive Gap":
                okg = okg and d.get("verification_state") == "interpretation"
            check("meta.gap.schema." + d.get("gap_id", "?"), okg)
        gapsec = body.split("## 研究空白", 1)[1].split("\n## ", 1)[0] if "## 研究空白" in body else ""
        numbered = len(re.findall(r"^\d+\. ", gapsec, flags=re.M))
        check("kp.gaps.count_matches_page." + rel, numbered == len(gs), "page=%d sidecars=%d" % (numbered, len(gs)))
        # index navigation
        short = os.path.relpath(p, KNOW)
        check("kp.indexed." + rel, bool({rel, short} & linked) or rel in idx,
              "not linked from 01knowledge/index.md")
    # .meta is never a knowledge page
    check("meta.not_knowledge_pages", all(".meta" not in os.path.relpath(p, ROOT) for p, _ in pages))
    # orphan pages
    orphans = [os.path.relpath(p, ROOT) for p, fm in pages
               if not ({os.path.relpath(p, ROOT), os.path.relpath(p, KNOW)} & linked)]
    check("knowledge.no_orphans", not orphans, ";".join(orphans))
    return pages

def validate_log_and_indexes(note_title=""):
    log = read(os.path.join(KNOW, "log.md"))
    rows = [l for l in log.split("\n") if l.startswith("| ") and "---" not in l]
    hdr = [r for r in rows if r.startswith("| 日期 ")][0]
    ncol = hdr.count("|") - 1
    body_rows = rows[1:]
    warn("log.append_only.row_count", len(body_rows) >= 1, "%d rows" % len(body_rows))
    if note_title:
        check("log.row_for_current_ingest", any(note_title in r for r in body_rows),
              "no append row mentioning: " + note_title)
    bad = [i for i, r in enumerate(body_rows) if r.count("|") - 1 != ncol]
    check("log.table.columns", not bad, "bad rows:" + ",".join(map(str, bad)))
    leaked = key_like_tokens("\n".join(body_rows))
    check("log.raw_keys_absent", not leaked, "raw zotero/pdf key visible in log:" + ";".join(sorted(leaked)))
    for f in ["文献索引.md", "研究主题索引.md", "研究方法索引.md", "字段补全检查.md"]:
        p = os.path.join(ROOT, "02vault/_index", f)
        if not os.path.isfile(p):
            continue
        lines = [l for l in read(p).split("\n") if l.startswith("|")]
        if not lines:
            continue
        n = structural_pipes(lines[0])
        bad = [i for i, l in enumerate(lines) if structural_pipes(l) != n]
        check("index.table_shape." + f, not bad, "rows with wrong column count:" + ",".join(map(str, bad)))
        ghosts = [t for l in lines for t, _ in wikilinks(l) if not resolve_link(t)]
        check("index.links_resolve." + f, not ghosts, ";".join(sorted(set(ghosts))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", required=True, help="相对 RESEARCH_VAULT_ROOT 的精读笔记路径")
    ap.add_argument("--pdf", required=True, help="原始 PDF 路径，用于逐字引文核验")
    a = ap.parse_args()
    fm = validate_note(os.path.join(ROOT, a.note), a.pdf)
    validate_knowledge()
    validate_log_and_indexes((fm or {}).get("title") or os.path.splitext(os.path.basename(a.note))[0])
    fails = [r for r in RESULTS if not r["ok"] and r.get("level", "FAIL") == "FAIL"]
    warns = [r for r in RESULTS if not r["ok"] and r.get("level") == "WARN"]
    rep = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "note": a.note, "checks": len(RESULTS), "failures": len(fails), "warnings": len(warns),
           "failed": [r["check"] + " :: " + r.get("detail", "") for r in fails],
           "warned": [r["check"] + " :: " + r.get("detail", "") for r in warns],
           "results": RESULTS}
    os.makedirs(os.path.join(KNOW, ".meta"), exist_ok=True)
    json.dump(rep, open(os.path.join(KNOW, ".meta/validation_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\nchecks=%d failures=%d warnings=%d" % (len(RESULTS), len(fails), len(warns)))
    for r in fails:
        print("  FAILED:", r["check"], "::", r.get("detail", ""))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
