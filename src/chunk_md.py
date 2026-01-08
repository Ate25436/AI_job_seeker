import re
from pathlib import Path
from typing import List, Optional, Tuple
import glob
import json


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
    markdown_text_list = markdown_text.split('\n')
    chunks = []
    current_heading = None
    current_content = [markdown_text_list.pop(0)]
    tree_bank = [current_content[0]] + [""] * 5
    current_level = 1

    for line in markdown_text_list:
        heading_match = re.match(heading_pattern, line)
        
        if heading_match:
            # 見出しが見つかった場合
            new_level = len(heading_match.group(1))
            if current_level < new_level:
                # 新しい見出しレベルが深い場合、現在のチャンクを保存
                current_content_str = '\n'.join(current_content).strip()
                tree_bank[current_level - 1] = current_content_str
                current_content = [line]
                current_level = new_level
                current_heading = heading_match.group(2).strip()
            else:
                chunks.append(
                    (current_heading, '\n'.join(filter(None, tree_bank[:current_level] + ['\n'.join(current_content).strip()])).strip())
                )
                current_content = [line]
                current_level = new_level
                current_heading = heading_match.group(2).strip()
        else:
            # 見出しでない場合、現在のコンテンツに追加
            current_content.append(line)
    if current_content != []:
        chunks.append(
            (current_heading, '\n'.join(filter(None, tree_bank[:current_level] + ['\n'.join(current_content).strip()])).strip())
        )
    
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

def chunk_mds():
    file_paths = glob.glob('information_source/**/*.md', recursive=True)
    print(file_paths)
    chunks = []
    for file_path in file_paths:
        file_name = Path(file_path).stem
        file_chunks = chunk_md_from_file(file_path)
        chunks.extend(
            [
                    {
                    "file_name": file_name,
                    "heading": chunk[0],
                    "content": chunk[1]
                } for chunk in file_chunks
            ]
        )
    return chunks

if __name__ == '__main__':
    print(json.dumps(chunk_mds(), ensure_ascii=False, indent=4))
