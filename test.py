import asyncio
from aiogtrans import Translator
from dotenv import load_dotenv
import os


load_dotenv()

print(f"HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
print(f"HTTPS_PROXY: {os.getenv('HTTPS_PROXY')}")


async def test_translation():
    translator = Translator()
    input_text = (
        "После внесения изменений в код создайте и запустите тесты снова. Если были правильно настроены параметры прокси и использовался корректный ключ (proxy или mounts), ошибка должна устраниться."
    )
    result = await translator.translate(input_text, dest="en")

    # Ожидаемый фрагмент перевода
    expected_fragment = "After making changes to the code, create and run the tests again."
    
    # Проверяем, содержит ли перевод ожидаемый фрагмент
    passed = expected_fragment in result.text
    
    print(f"Test Translation for multiple sentences: {'Passed' if passed else 'Failed'}")
    print(f"Translated Text: {result.text}")


async def test_language_detection():
    translator = Translator()
    detected = await translator.detect("Bonjour")
    passed = detected.lang == "fr" and detected.confidence > 0.2
    print(f"Test Language Detection: {'Passed' if passed else 'Failed'}")
    print(f"Detected Language: {detected.lang}, Confidence: {detected.confidence}")


async def test_bulk_translation():
    translator = Translator()
    phrases = ["Привет", "Как дела?", "До свидания"]
    translations = await translator.translate(phrases, dest="en")
    expected = ["Hello", "How are you?", "Goodbye"]
    passed = [translation.text for translation in translations] == expected
    print(f"Test Bulk Translation: {'Passed' if passed else 'Failed'}")
    for origin, translation in zip(phrases, translations):
        print(f"{origin} -> {translation.text}")


async def test_custom_service_url():
    translator = Translator(service_urls=["translate.google.co.kr"])
    result = await translator.translate("안녕하세요", dest="en")
    passed = result.text in ["Hello", "Hi"]
    print(f"Test Custom Service URL: {'Passed' if passed else 'Failed'}")
    print(f"Translated Text: {result.text}")


async def test_http2_support():
    translator = Translator()
    result = await translator.translate("테스트", dest="en")
    passed = result._response.http_version == "HTTP/2"
    print(f"Test HTTP/2 Support: {'Passed' if passed else 'Failed'}")
    print(f"HTTP Version: {result._response.http_version}")


async def main():
    print("Starting aiogtrans tests...\n")
    await test_translation()
    # await test_language_detection()
    # await test_bulk_translation()
    # await test_custom_service_url()
    # await test_http2_support()
    print("\nAll tests completed.")


if __name__ == "__main__":
    asyncio.run(main())
