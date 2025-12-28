import auth
import ocr_service
import utils

# 确保你把一张图片放在了项目文件夹里，名字叫 test.jpg
IMAGE_PATH = "test.jpg"

def main():
    print("1. 获取 Token...")
    token = auth.get_access_token()
    if not token: return

    print("2. 识别图片...")
    result = ocr_service.get_text_from_image(IMAGE_PATH, token)

    print("3. 提取信息...")
    info = utils.extract_info(result)
    print("=== 最终结果 ===", info)

if __name__ == "__main__":
    main()