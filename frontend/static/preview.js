const imageInput = document.getElementById("image-input");
const imagePreview = document.getElementById("image-preview");
const fileName = document.getElementById("file-name");

imageInput.addEventListener("change", () => {
    const [file] = imageInput.files;
    if (!file) {
        imagePreview.style.display = "none";
        imagePreview.removeAttribute("src");
        fileName.textContent = "No file selected";
        return;
    }
    imagePreview.src = URL.createObjectURL(file);
    imagePreview.style.display = "block";
    fileName.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
});
