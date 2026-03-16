import flet as ft
from flet_main import FletPhotoboothApp

def main(page: ft.Page):
    # Khởi tạo ứng dựng với giao diện Liquid Glass đã hoàn thiện
    FletPhotoboothApp(page)

if __name__ == "__main__":
    # Chạy ứng dụng Flet chính thức
    ft.app(target=main)
