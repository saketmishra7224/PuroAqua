import cv2
import numpy as np
import mysql.connector
from datetime import datetime

# Threshold to determine if a color is too far from all predefined colors
THRESHOLD = 15.0  

# Define RGB color levels and their names
color_levels = [
    {"name": "Sea Nymph", "rgb": (130, 159, 152), "level": 1},
    {"name": "Metallic Seaweed", "rgb": (38, 127, 140), "level": 2},
    {"name": "Metallic Seaweed", "rgb": (26, 127, 147), "level": 3},
    {"name": "Regal Blue", "rgb": (0, 71, 119), "level": 4},
    {"name": "Cod Grey", "rgb": (13, 12, 12), "level": 5},
]

# Function to calculate the Euclidean distance between two RGB colors
def calculate_color_distance(color1, color2):
    return np.sqrt(sum((e1 - e2) ** 2 for e1, e2 in zip(color1, color2)))

# Function to get the closest color level based on the average RGB values
def get_color_level(avg_color_rgb):
    closest_color = min(color_levels, key=lambda c: calculate_color_distance(c["rgb"], avg_color_rgb))
    distance = calculate_color_distance(closest_color["rgb"], avg_color_rgb)

    # Check if the distance exceeds the threshold
    if distance > THRESHOLD:
        return "Unknown", None  # Return "Unknown" if no close match found

    return closest_color["name"], closest_color["level"]

# Function to insert the event into the MySQL database
def insert_event_into_db(level):
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host="localhost",  # Replace with your MySQL server address if needed
            user="your_username",  # Replace with your MySQL username
            password="your_password",  # Replace with your MySQL password
            database="water_quality"  # Replace with your database name
        )

        # Get the current date and time
        current_time = datetime.now()

        # SQL query to insert data into the table
        sql_insert_query = "INSERT INTO silver_ion_events (event_time, alert_level) VALUES (%s, %s)"
        cursor = connection.cursor()
        cursor.execute(sql_insert_query, (current_time, level))
        connection.commit()

        print("Event inserted into the database successfully")

    except mysql.connector.Error as error:
        print(f"Failed to insert event into MySQL table: {error}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Initialize the webcam (typically index 0)
cap = cv2.VideoCapture(0)

while True:
    # Capture frame-by-frame from the webcam
    ret, frame = cap.read()
    if not ret:
        break

    # Get frame dimensions
    height, width, _ = frame.shape

    # Define a centered rectangle (you can adjust size as needed)
    center_x, center_y = width // 2, height // 2
    rect_width, rect_height = width // 4, height // 4
    top_left_x = center_x - rect_width // 2
    top_left_y = center_y - rect_height // 2
    bottom_right_x = center_x + rect_width // 2
    bottom_right_y = center_y + rect_height // 2

    # Draw the rectangle on the frame (for visualization)
    cv2.rectangle(frame, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (0, 255, 0), 2)

    # Crop the region of interest (ROI) inside the rectangle
    roi = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]

    # Calculate the average color in the rectangle (in BGR format)
    avg_color_bgr = cv2.mean(roi)[:3]  # Ignore alpha channel
    avg_color_rgb = tuple(int(c) for c in avg_color_bgr[::-1])  # Convert BGR to RGB

    # Get the closest color level and name
    color_name, alert_level = get_color_level(avg_color_rgb)

    # Print the average color and corresponding alert level
    print(f"Average color: {avg_color_rgb}, Color Name: {color_name}, Alert Level: {alert_level}")

    # If a valid alert level is detected, log it in the database and display alert
    if alert_level is not None:
        print(f"ALERT: {color_name} detected with Level {alert_level}")
        insert_event_into_db(alert_level)  # Insert the event into the database

        # Display the alert on the video feed
        alert_text = f"{color_name} - Level {alert_level}"
        cv2.putText(frame, alert_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
        # Display "Unknown Color" message if no close match is found
        cv2.putText(frame, "Unknown Color Detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    # Display the original frame with rectangle
    cv2.imshow("Original", frame)

    # Break the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
