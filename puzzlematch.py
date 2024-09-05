import os
from flask import Flask, request, jsonify, send_file, render_template, make_response
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
from io import BytesIO

app = Flask(__name__, static_folder='static')

# Configure maximum file size and allowed extensions
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Directory to store uploaded puzzle images
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_puzzle', methods=['POST'])
def upload_puzzle():
    if 'puzzle' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    puzzle = request.files['puzzle']

    if puzzle.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(puzzle.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        filename = secure_filename(puzzle.filename)
        puzzle_path = os.path.join(UPLOAD_FOLDER, filename)
        puzzle.save(puzzle_path)
        return jsonify({'message': 'Puzzle image uploaded successfully'})

    except Exception as e:
        app.logger.error('Error uploading puzzle image: %s', str(e))
        return jsonify({'error': 'Error uploading puzzle image'}), 500


@app.route('/clear_puzzle', methods=['POST'])
def clear_puzzle():
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'message': 'Puzzle image cleared successfully'})

    except Exception as e:
        app.logger.error('Error clearing puzzle image: %s', str(e))
        return jsonify({'error': 'Error clearing puzzle image'}), 500


@app.route('/match', methods=['POST'])
def match_piece():
    if 'piece' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    piece = request.files['piece']

    if piece.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(piece.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # Check if a puzzle image is available
        puzzle_files = os.listdir(UPLOAD_FOLDER)
        if len(puzzle_files) == 0:
            return jsonify({'error': 'No puzzle image found. Please upload a puzzle image first.'}), 400

        puzzle_path = os.path.join(UPLOAD_FOLDER, puzzle_files[0])
        puzzle_img = cv2.imread(puzzle_path)
        piece_img = cv2.imdecode(np.fromstring(piece.read(), np.uint8), cv2.IMREAD_COLOR)

        # Create SIFT detector
        sift = cv2.SIFT_create()

        # Detect keypoints and compute descriptors
        keypoints_puzzle, descriptors_puzzle = sift.detectAndCompute(puzzle_img, None)
        keypoints_piece, descriptors_piece = sift.detectAndCompute(piece_img, None)

        # Create FLANN matcher
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        # Match descriptors
        matches = flann.knnMatch(descriptors_piece, descriptors_puzzle, k=2)

        # Apply ratio test to filter good matches
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        # Extract the matched keypoints
        piece_points = np.float32([keypoints_piece[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        puzzle_points = np.float32([keypoints_puzzle[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Find homography matrix
        M, _ = cv2.findHomography(piece_points, puzzle_points, cv2.RANSAC, 5.0)

        # Get the dimensions of the piece image
        h, w = piece_img.shape[:2]

        # Transform the corners of the piece image
        corners = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        transformed_corners = cv2.perspectiveTransform(corners, M)

        # Draw the matched region on the puzzle image
        cv2.polylines(puzzle_img, [np.int32(transformed_corners)], True, (0, 255, 0), 2, cv2.LINE_AA)

        _, buffer = cv2.imencode('.png', puzzle_img)
        buffer = BytesIO(buffer)

        response = make_response(send_file(buffer, mimetype='image/png'))
        response.headers['Content-Disposition'] = 'inline; filename=result.png'

        return response

    except Exception as e:
        app.logger.error('Error processing images: %s', str(e))
        return jsonify({'error': 'Error processing images'}), 500


if __name__ == '__main__':
    app.run(debug=os.environ.get('DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
