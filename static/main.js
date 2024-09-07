const puzzleForm = document.getElementById('puzzle-form');
const pieceForm = document.getElementById('piece-form');
const clearPuzzleBtn = document.getElementById('clear-puzzle');
const message = document.getElementById('message');
const result = document.getElementById('result');

puzzleForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const puzzleFile = document.getElementById('puzzle').files[0];

    const formData = new FormData();
    formData.append('puzzle', puzzleFile);

    try {
        const response = await fetch('/upload_puzzle', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            message.textContent = data.message;
        } else {
            message.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        console.error('Error:', error);
        message.textContent = 'An error occurred. Please try again later.';
    }
});

clearPuzzleBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/clear_puzzle', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            message.textContent = data.message;
        } else {
            message.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        console.error('Error:', error);
        message.textContent = 'An error occurred. Please try again later.';
    }
});

pieceForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const pieceFile = document.getElementById('piece').files[0];
    const matchingTechnique = document.getElementById('matching-technique').value;

    const formData = new FormData();
    formData.append('piece', pieceFile);
    formData.append('matching_technique', matchingTechnique);

    message.textContent = '';
    result.innerHTML = '';

    try {
        const response = await fetch('/match', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const imgUrl = URL.createObjectURL(blob);
            const img = document.createElement('img');
            img.src = imgUrl;
            result.appendChild(img);
        } else {
            const data = await response.json();
            message.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        console.error('Error:', error);
        message.textContent = 'An error occurred. Please try again later.';
    }
});
