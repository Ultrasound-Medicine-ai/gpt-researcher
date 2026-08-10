import re
import markdown
from typing import List, Dict

def extract_headers(markdown_text: str) -> List[Dict]:
    """
    Extract headers from markdown text.

    Args:
        markdown_text (str): The markdown text to process.

    Returns:
        List[Dict]: A list of dictionaries representing the header structure.
    """
    headers = []
    parsed_md = markdown.markdown(markdown_text)
    lines = parsed_md.split("\n")

    stack = []
    for line in lines:
        if line.startswith("<h") and len(line) > 2 and line[2].isdigit():
            level = int(line[2])
            header_text = line[line.index(">") + 1 : line.rindex("<")]

            while stack and stack[-1]["level"] >= level:
                stack.pop()

            header = {
                "level": level,
                "text": header_text,
            }
            if stack:
                stack[-1].setdefault("children", []).append(header)
            else:
                headers.append(header)

            stack.append(header)

    return headers

def extract_sections(markdown_text: str) -> List[Dict[str, str]]:
    """
    Extract all written sections from subtopic report.

    Args:
        markdown_text (str): Subtopic report text.

    Returns:
        List[Dict[str, str]]: List of sections, each section is a dictionary containing
        'section_title' and 'written_content'.
    """
    sections = []
    parsed_md = markdown.markdown(markdown_text)
    
    pattern = r'<h\d>(.*?)</h\d>(.*?)(?=<h\d>|$)'
    matches = re.findall(pattern, parsed_md, re.DOTALL)
    
    for title, content in matches:
        clean_content = re.sub(r'<.*?>', '', content).strip()
        if clean_content:
            sections.append({
                "section_title": title.strip(),
                "written_content": clean_content
            })
    
    return sections

def table_of_contents(markdown_text: str) -> str:
    """
    Generate a table of contents for the given markdown text.

    Args:
        markdown_text (str): The markdown text to process.

    Returns:
        str: The generated table of contents.
    """
    def generate_table_of_contents(headers, indent_level=0):
        toc = ""
        for header in headers:
            toc += " " * (indent_level * 4) + "- " + header["text"] + "\n"
            if "children" in header:
                toc += generate_table_of_contents(header["children"], indent_level + 1)
        return toc

    try:
        headers = extract_headers(markdown_text)
        toc = "## Table of Contents\n\n" + generate_table_of_contents(headers)
        return toc
    except Exception as e:
        print("table_of_contents Exception : ", e)
        return markdown_text

def strip_apa_inline_citations(report_markdown: str) -> str:
    """Remove APA-style inline source lines such as 'Source: (Author, n.d.)'."""
    cleaned = re.sub(
        r"\n\s*Source:\s*\([^)\n]+\)\s*",
        "\n",
        report_markdown,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\n\s*Source:\s*\[[^\]\n]+\]\([^)\n]+\)\s*",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def strip_existing_references_section(report_markdown: str) -> str:
    """
    Remove an LLM-generated References / 参考文献 section from the report tail.

    Args:
        report_markdown: The markdown report text.

    Returns:
        Report markdown without a trailing references section.
    """
    patterns = [
        r"\n##\s*(References|参考文献)\s*\n[\s\S]*$",
        r"\n#\s*(References|参考文献)\s*\n[\s\S]*$",
        r"\n(?:References|参考文献)\s*\n[\s\S]*$",
    ]
    cleaned = report_markdown
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.rstrip()


def add_numbered_references(
    report_markdown: str,
    registry,
    references_heading: str | None = None,
) -> str:
    """
    Append a deterministic numbered reference list to the report.

    Args:
        report_markdown: The markdown report text.
        registry: SourceRegistry instance with numbered sources.
        references_heading: Optional markdown heading for the references section.

    Returns:
        Report markdown with numbered references appended.
    """
    reference_section = registry.format_reference_list(references_heading)
    if not reference_section:
        return report_markdown
    return f"{report_markdown.rstrip()}\n\n{reference_section}"


def strip_invalid_numbered_citations(report_markdown: str, source_count: int) -> str:
    """Remove numbered citations that cannot resolve to a verified source.

    The legacy Writer can emit a citation number on its own.  Keeping an
    unresolved ``[n]`` would make the report look sourced even when no
    citable original text exists, so this is a final delivery-time guard.
    """
    def _replace(match: re.Match) -> str:
        number = int(match.group(1))
        return match.group(0) if 1 <= number <= source_count else ""

    return re.sub(r"\[(\d{1,3})\]", _replace, report_markdown)


def normalize_numbered_report(
    report_markdown: str,
    registry,
    references_heading: str | None = None,
) -> str:
    """Strip APA-style citations and append deterministic numbered references."""
    cleaned = strip_apa_inline_citations(report_markdown)
    cleaned = strip_existing_references_section(cleaned)
    cleaned = strip_invalid_numbered_citations(
        cleaned, len(getattr(registry, "entries", []) or [])
    )
    return add_numbered_references(cleaned, registry, references_heading)


def add_references(report_markdown: str, visited_urls: set) -> str:
    """
    Add references to the markdown report.

    Args:
        report_markdown (str): The existing markdown report.
        visited_urls (set): A set of URLs that have been visited during research.

    Returns:
        str: The updated markdown report with added references.
    """
    try:
        url_markdown = "\n\n\n## References\n\n"
        url_markdown += "".join(f"- [{url}]({url})\n" for url in visited_urls)
        updated_markdown_report = report_markdown + url_markdown
        return updated_markdown_report
    except Exception as e:
        print(f"Encountered exception in adding source urls : {e}")
        return report_markdown
