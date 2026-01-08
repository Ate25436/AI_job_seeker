import re
from typing import List, Tuple


def chunk_md(markdown_text: str) -> List[Tuple[str, str]]:
    """
    Markdown文字列を見出しごとにチャンキングします。
    
    Args:
        markdown_text: チャンキング対象のMarkdown文字列
        
    Returns:
        (見出し, 内容) のタプルのリスト
    """
    # 見出しパターン：# または ## または ### など
    heading_pattern = r'^(#{1,6})\s+(.+)$'
    
    chunks = []
    current_heading = None
    current_content = []
    
    for line in markdown_text.split('\n'):
        heading_match = re.match(heading_pattern, line)
        
        if heading_match:
            # 新しい見出しが見つかった場合、前のチャンクを保存
            if current_heading is not None:
                chunks.append((current_heading, '\n'.join(current_content).strip()))
            
            # 新しい見出しを開始
            current_heading = line
            current_content = []
        else:
            # 見出しの内容として行を追加
            if current_heading is not None:
                current_content.append(line)
    
    # 最後のチャンクを保存
    if current_heading is not None:
        chunks.append((current_heading, '\n'.join(current_content).strip()))
    
    return chunks


def chunk_md_from_file(file_path: str) -> List[Tuple[str, str]]:
    """
    ファイルからMarkdownを読み込んでチャンキングします。
    
    Args:
        file_path: Markdownファイルのパス
        
    Returns:
        (見出し, 内容) のタプルのリスト
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    return chunk_md(markdown_text)


if __name__ == '__main__':
    # テスト用のサンプルMarkdown
    sample_md = """# メイン見出し
    
これはメイン見出しの内容です。

## サブ見出し1

サブ見出し1の内容です。
複数行あります。

## サブ見出し2

サブ見出し2の内容です。

### さらに深い見出し

さらに深い見出しの内容です。
"""
    
    chunks = chunk_md(sample_md)
    for heading, content in chunks:
        print(f"見出し: {heading}")
        print(f"内容: {content}")
        print("---")
