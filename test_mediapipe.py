import mediapipe as mp


def main():
    print("MediaPipe version:", mp.__version__)
    mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
    )
    print("MediaPipe Hands initialized successfully")


if __name__ == "__main__":
    main()
