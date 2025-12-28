import auth
import ocr_service
import utils

IMAGE_PATH = "test.jpg"


def main():
    print("1. Getting token...")
    token = auth.get_access_token()
    if not token:
        return

    print("2. Recognizing image...")
    result = ocr_service.get_text_from_image(IMAGE_PATH, token)

    print("3. Extracting info...")
    info = utils.extract_info(result)
    print("=== Result ===", info)


if __name__ == "__main__":
    main()
