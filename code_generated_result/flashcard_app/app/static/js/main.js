document.addEventListener('DOMContentLoaded', function() {
    // Functionality for revealing the back of the card.
    const flashcards = document.querySelectorAll('.flashcard');

    flashcards.forEach(flashcard => {
        flashcard.addEventListener('click', function() {
            this.classList.toggle('flipped');
        });
    });

    // Functionality for handling delete confirmation (if needed)
    const deleteButtons = document.querySelectorAll('.delete-card-button'); // Assuming this class exists in your HTML

    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent the default link behavior

            const cardId = this.dataset.cardId; // Assuming the card ID is stored as a data attribute
            const confirmDelete = confirm("Are you sure you want to delete this flashcard?");

            if (confirmDelete) {
                // Construct the delete URL (assuming POST method, as per the design doc)
                const deleteUrl = `/flashcards/${cardId}/delete`;

                // Create a form and submit it programmatically (to handle POST request via a link)
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = deleteUrl;

                // Add a CSRF token (if you're using CSRF protection in Flask) - adapt the name to your actual token name
                const csrfToken = document.querySelector('input[name="csrf_token"]');
                if (csrfToken) {
                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrf_token';
                    csrfInput.value = csrfToken.value; //Get it from a field in template
                    form.appendChild(csrfInput);
                }

                document.body.appendChild(form); // Append the form to the body
                form.submit(); // Submit the form

            } else {
                // Do nothing if the user cancels the deletion
                console.log("Deletion cancelled.");
            }
        });
    });
});