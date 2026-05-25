from setuptools import find_packages, setup


setup(
    name="phone-trackpad",
    version="0.1.0",
    description="Use an iPhone browser as a Windows trackpad over a local network.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    packages=find_packages(),
    include_package_data=True,
    package_data={"phone_trackpad": ["static/index.html"]},
    install_requires=[
        "websockets>=14.0",
        "pyautogui>=0.9.54",
        "qrcode[pil]>=7.0",
        "Pillow>=9.0",
        "pyperclip>=1.8.0",
    ],
    entry_points={"console_scripts": ["phone-trackpad=phone_trackpad.__main__:main"]},
)
