import asyncio, logging
from pathlib import Path
from docx import Document
from docx.shared import Pt
from playwright.async_api import async_playwright

# ================= 只需要改这一行 =================
START_URL  = "https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=1249166491&courseId=267267560&clazzid=155149366&cpi=485007833&enc=bd56a625741011a7f4ede29905cfc6a8&mooc2=1&hidetype=0&fanyaVersion=0&openc=756627ecb9493c46e51c6da4d286f3df" 
# ==================================================

AUTH_FILE = Path("auth.json")           
OUTPUT_FILE = Path("我的测验题库.docx") 

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def find_questions_page(page):
    """遍历所有iframe，找到真正包含题目的那个frame"""
    # 1. 先检查主页面
    if await page.locator(".TiMu").count() > 0:
        return page
    
    # 2. 遍历所有子frame
    for frame in page.frames:
        try:
            if await frame.locator(".TiMu").count() > 0:
                logging.info("  🔄 穿透 iframe 成功，找到题目所在页面！")
                return frame
        except:
            continue
    return None

async def extract_and_save(page, doc, existing_texts):
    """在找到的页面中提取题目并保存"""
    added_count = 0
    
    # 1. 点击“章节测验”标签（使用正确的语法）
    # 使用 get_by_text，这是Playwright推荐的文本定位方式，更稳定
    try:
        tab = page.get_by_text("章节测验").first
        if await tab.count() > 0 and await tab.is_visible():
            logging.info("👉 点击【章节测验】标签...")
            await tab.click()
            await page.wait_for_timeout(4000) # 给超星足够的加载时间
    except Exception as e:
        logging.warning(f"点击测验标签失败，继续尝试直接找题: {e}")

    # 2. 穿透iframe找到题目所在页面
    target_page = await find_questions_page(page)
    if not target_page:
        logging.info("⚠️ 扫描完毕：当前页面（含iframe）均未发现题目。")
        return 0

    # 3. 抓取题目
    boxes = await target_page.locator(".TiMu").all()
    logging.info(f"✅ 找到 {len(boxes)} 道题，开始提取...")
    
    for i, box in enumerate(boxes, 1):
        try:
            raw_text = await box.inner_text()
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            cleaned_lines = [line for line in lines if "AI讲解" not in line and "收藏" not in line]
            
            snippet = '\n'.join(cleaned_lines)[:30]
            
            if not any(snippet in text for text in existing_texts):
                for line in cleaned_lines:
                    doc.add_paragraph(line)
                doc.add_paragraph("")
                existing_texts.append(snippet)
                added_count += 1
                logging.info(f"  [+] {snippet}...")
            else:
                logging.info(f"  [-] 重复跳过：{snippet}...")
        except Exception as e:
            logging.error(f"  [x] 提取失败：{e}")
            
    return added_count

async def main():
    if OUTPUT_FILE.exists():
        doc = Document(OUTPUT_FILE)
    else:
        doc = Document()
        doc.styles["Normal"].font.name = '宋体'
        doc.styles["Normal"].font.size = Pt(11)
        
    existing_texts = [p.text for p in doc.paragraphs if p.text.strip()]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False) 
        context = await browser.new_context(storage_state=str(AUTH_FILE) if AUTH_FILE.exists() else None)
        page = await context.new_page()

        logging.info(f"正在打开网页：{START_URL}")
        await page.goto(START_URL)
        
        if not AUTH_FILE.exists():
            print("\n请在弹出的浏览器中登录，并跳转到第一章节，然后回终端按回车...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            await context.storage_state(path=str(AUTH_FILE))

        chapter_num = 1
        while True:
            logging.info(f"\n================ 处理第 {chapter_num} 节 ================")
            
            # 1. 抓取当前页面
            added = await extract_and_save(page, doc, existing_texts)
            if added > 0:
                doc.save(OUTPUT_FILE)
                logging.info(f"💾 已成功写入 {added} 道题。")

            # 2. 准备点击【下一节】
            logging.info("🔍 寻找【下一节】按钮...")
            try:
                # 强制滚动到底部，确保按钮加载
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
            except:
                pass

            # 3. 使用更可靠的定位器找按钮
            # 根据GitHub脚本实践，ID是 #prevNextFocusNext 或 .prevNextFocusNext
            next_btn = page.locator("#prevNextFocusNext, .prevNextFocusNext").first
            
            if await next_btn.count() == 0:
                logging.info("🏁 页面找不到【下一节】按钮，可能已经全部学完。")
                break
                
            btn_class = await next_btn.get_attribute("class")
            if btn_class and "disabled" in btn_class.lower():
                logging.info("🏁 【下一节】按钮已置灰，到底了！结束。")
                break

            # 4. 点击【下一节】
            logging.info("⏭️ 点击【下一节】...")
            try:
                await next_btn.click(force=True)
                await page.wait_for_timeout(5000) # 等待新章节加载
                chapter_num += 1
            except Exception as e:
                logging.error(f"❌ 点击下一节报错：{e}")
                break

        logging.info(f"\n🎉 任务结束！请查看【{OUTPUT_FILE}】")
        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())