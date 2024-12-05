// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Theme handling
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    
    // Profile image preview
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.createElement('img');
                    preview.src = e.target.result;
                    preview.className = 'img-fluid mb-3 post-image';
                    const container = document.querySelector('.card-body');
                    const existingPreview = container.querySelector('img');
                    if (existingPreview) {
                        container.removeChild(existingPreview);
                    }
                    container.insertBefore(preview, container.querySelector('button'));
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }

    // Initialize notifications
    const notificationsDropdown = document.getElementById('notificationsDropdown');
    if (notificationsDropdown) {
        notificationsDropdown.addEventListener('click', function() {
            document.querySelector('.notification-badge').style.display = 'none';
        });
    }

    // Auto resize textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
});

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    fetch('/settings/theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
}

function toggleLike(postId) {
    fetch(`/like/${postId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const btn = document.querySelector(`.like-btn[data-post-id="${postId}"]`);
            const icon = btn.querySelector('i');
            const count = btn.querySelector('.likes-count');
            
            icon.classList.toggle('bi-heart');
            icon.classList.toggle('bi-heart-fill');
            count.textContent = data.likes_count;
        }
    });
}

function toggleBookmark(postId) {
    fetch(`/bookmark/${postId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const btn = document.querySelector(`.bookmark-btn[data-post-id="${postId}"]`);
            const icon = btn.querySelector('i');
            
            icon.classList.toggle('bi-bookmark');
            icon.classList.toggle('bi-bookmark-fill');
        }
    });
}

function sharePost(postId) {
    const url = `${window.location.origin}/post/${postId}`;
    navigator.clipboard.writeText(url)
        .then(() => alert('Link copied to clipboard!'));
}

let editor = null;
function initPostEditor(postId) {
    const post = document.querySelector(`#post-${postId}`);
    const content = post.querySelector('.post-content');
    const oldContent = content.textContent;
    content.style.display = 'none';
    
    editor = document.createElement('textarea');
    editor.className = 'form-control mb-2';
    editor.value = oldContent;
    
    const controls = document.createElement('div');
    controls.className = 'mb-3';
    controls.innerHTML = `
        <button class="btn btn-rebs btn-sm me-2" onclick="updatePost(${postId})">Save</button>
        <button class="btn btn-secondary btn-sm" onclick="cancelEdit(${postId}, '${oldContent}')">Cancel</button>
    `;
    
    content.insertAdjacentElement('afterend', editor);
    editor.insertAdjacentElement('afterend', controls);
}

function updatePost(postId) {
    if (!editor) return;
    
    fetch(`/post/${postId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            content: editor.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

function cancelEdit(postId, oldContent) {
    const post = document.querySelector(`#post-${postId}`);
    const content = post.querySelector('.post-content');
    content.style.display = 'block';
    content.textContent = oldContent;
    
    if (editor) {
        editor.nextElementSibling.remove(); // Remove controls
        editor.remove();
        editor = null;
    }
}

function deletePost(postId) {
    if (!confirm('Are you sure you want to delete this post?')) return;
    
    fetch(`/post/${postId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

function replyToComment(commentId) {
    const commentElement = document.querySelector(`#comment-${commentId}`);
    if (commentElement.querySelector('.reply-form')) return;
    
    const replyForm = document.createElement('form');
    replyForm.className = 'reply-form mt-2';
    replyForm.innerHTML = `
        <div class="input-group input-group-sm">
            <input type="text" class="form-control" placeholder="Write a reply...">
            <button type="submit" class="btn btn-outline-secondary">Reply</button>
        </div>
    `;
    
    replyForm.onsubmit = function(e) {
        e.preventDefault();
        const content = this.querySelector('input').value;
        
        fetch(`/reply/${commentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({content})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            }
        });
    };
    
    commentElement.appendChild(replyForm);
}