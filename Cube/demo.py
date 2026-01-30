import os
from PIL import Image


def check_image_files():
    """使用PIL检查图片文件"""
    images = [
        'D:\\PyhtonCodes\\Cube\\攻击1.png',
        'D:\\PyhtonCodes\\Cube\\攻击2.png',
        'D:\\PyhtonCodes\\Cube\\攻击3.png',
        'D:\\PyhtonCodes\\Cube\\攻击4.png'
    ]

    for img_path in images:
        print(f"\n检查: {img_path}")
        print(f"文件存在: {os.path.exists(img_path)}")

        if os.path.exists(img_path):
            print(f"文件大小: {os.path.getsize(img_path)} 字节")

            # 尝试用PIL打开
            try:
                with Image.open(img_path) as img:
                    print(f"✓ PIL可以打开")
                    print(f"  格式: {img.format}")
                    print(f"  尺寸: {img.size}")
                    print(f"  模式: {img.mode}")

                    # 转换为RGB并保存为新的PNG文件
                    if img.mode != 'RGB':
                        print(f"  转换模式: {img.mode} -> RGB")
                        rgb_img = img.convert('RGB')
                        new_path = img_path.replace('.png', '_fixed.png')
                        rgb_img.save(new_path)
                        print(f"  已保存修复版: {new_path}")

            except Exception as e:
                print(f"✗ PIL打开失败: {e}")

                # 尝试读取二进制文件
                try:
                    with open(img_path, 'rb') as f:
                        header = f.read(8)
                        print(f"  文件头: {header}")
                        if header[:8] == b'\x89PNG\r\n\x1a\n':
                            print("  是有效的PNG文件头")
                        else:
                            print("  不是标准的PNG文件头")
                except Exception as e2:
                    print(f"  读取二进制失败: {e2}")


# 运行检查
check_image_files()
