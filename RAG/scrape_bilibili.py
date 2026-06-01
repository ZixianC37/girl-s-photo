#!/usr/bin/env python3
"""
Scrape Bilibili video content for GraphRAG+Neo4j tutorial series
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os

def scrape_bilibili_video(url):
    """Scrape video content from Bilibili"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com/'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = soup.find('h1', class_='video-title').text.strip() if soup.find('h1', class_='video-title') else 'No Title Found'

        # Extract description
        desc = soup.find('div', id='desc').text.strip() if soup.find('div', id='desc') else 'No Description Found'

        # Extract video info
        info_text = soup.find('div', class_='video-info').text if soup.find('div', class_='video-info') else ''

        # Extract watch info
        watch_info = soup.find('div', class_='watch-info').text if soup.find('div', class_='watch-info') else ''

        # Extract danmaku comments if available
        danmaku_container = soup.find('div', class_='danmaku-container')
        danmaku_comments = []
        if danmaku_container:
            comments = danmaku_container.find_all('span', class_='danmaku-text')
            danmaku_comments = [comment.text.strip() for comment in comments]

        # Extract tags
        tags = []
        tag_elements = soup.find_all('span', class_='tag')
        for tag in tag_elements:
            tags.append(tag.text.strip())

        return {
            'title': title,
            'url': url,
            'description': desc,
            'info': info_text,
            'watch_info': watch_info,
            'danmaku_comments': danmaku_comments,
            'tags': tags,
            'raw_html': response.text[:5000]  # First 5000 chars of raw HTML for debugging
        }

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def main():
    """Main function to scrape all video parts"""
    base_url = "https://www.bilibili.com/video/BV1dSGB6iEqg/?p={}"

    # Create output directory
    output_dir = "/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge"
    os.makedirs(output_dir, exist_ok=True)

    # Scrape all parts
    results = []
    for i in range(5, 17):  # Parts 5-16
        print(f"Scraping part {i}...")
        url = base_url.format(i)
        result = scrape_bilibili_video(url)
        if result:
            result['part'] = i
            results.append(result)
            time.sleep(2)  # Be polite to the server

    # Save results
    output_file = os.path.join(output_dir, "bilibili-series2-p5-p16-raw-notes.md")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# GraphRAG+Neo4j 知识图谱医药问答系统实战 - 视频内容笔记\n\n")
        f.write(f"Series: [1小时搞定！基于【GraphRAG+Neo4j】打造知识图谱的本地RAG知识库！](https://www.bilibili.com/video/BV1dSGB6iEqg/)\n\n")
        f.write("## 详细内容\n\n")

        for result in results:
            f.write(f"\n### Part {result['part']}: {result['title']}\n")
            f.write(f"**URL:** {result['url']}\n\n")
            f.write(f"**描述:** {result['description']}\n\n")
            f.write(f"**视频信息:** {result['info']}\n\n")
            f.write(f"**观看信息:** {result['watch_info']}\n\n")
            f.write(f"**标签:** {', '.join(result['tags'])}\n\n")
            if result['danmaku_comments']:
                f.write(f"**弹幕评论:**\n")
                for comment in result['danmaku_comments'][:10]:  # Show first 10 comments
                    f.write(f"- {comment}\n")
                f.write("\n")
            f.write("---\n\n")

    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()