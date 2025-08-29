(function () {
	const dropzone = document.getElementById('dropzone');
	const fileInput = document.getElementById('fileInput');
	const lengthSelect = document.getElementById('length');
	const summarizeBtn = document.getElementById('summarizeBtn');
	const btnText = summarizeBtn.querySelector('.btn-text');
	const btnSpinner = summarizeBtn.querySelector('.spinner');
	const statusBox = document.getElementById('status');
	const resultBox = document.getElementById('result');
	const summaryEl = document.getElementById('summary');
	const keypointsEl = document.getElementById('keypoints');

	const thumb = document.getElementById('thumb');
	const filenameEl = document.getElementById('filename');
	const filesizeEl = document.getElementById('filesize');

	// Stop dropzone click from doubling the native input click via the label
	const chooseLabel = document.querySelector('label.button');
	if (chooseLabel) {
		chooseLabel.addEventListener('click', (e) => {
			e.stopPropagation();
		});
	}

	let selectedFile = null;

	function setStatus(text, kind = 'info') {
		statusBox.textContent = text;
		statusBox.classList.remove('hidden', 'error', 'success', 'info');
		statusBox.classList.add(kind);
	}

	function clearStatus() {
		statusBox.textContent = '';
		statusBox.classList.add('hidden');
	}

	function humanSize(n) {
		if (!n) return '0 B';
		const units = ['B','KB','MB','GB'];
		let i = 0; let s = n;
		while (s >= 1024 && i < units.length - 1) { s /= 1024; i++; }
		return `${s.toFixed(1)} ${units[i]}`;
	}

	function showPreview(file) {
		filenameEl.textContent = file.name;
		filesizeEl.textContent = `${file.type || 'Unknown type'} • ${humanSize(file.size)}`;

		if (file.type.startsWith('image/')) {
			const url = URL.createObjectURL(file);
			thumb.innerHTML = '';
			const img = document.createElement('img');
			img.src = url;
			thumb.appendChild(img);
		} else {
			thumb.innerHTML = '<span class="muted">PDF</span>';
		}
	}

	function setLoading(loading) {
		if (loading) {
			summarizeBtn.setAttribute('disabled', 'true');
			btnSpinner.classList.remove('hidden');
			btnText.textContent = 'Summarizing…';
		} else {
			summarizeBtn.removeAttribute('disabled');
			btnSpinner.classList.add('hidden');
			btnText.textContent = 'Summarize';
		}
	}

	function selectFile(file) {
		selectedFile = file;
		showPreview(file);
		setStatus(`Selected: ${file.name}`, 'info');
		resultBox.classList.add('hidden');
	}

	// Dropzone interactions
	dropzone.addEventListener('dragover', (e) => {
		e.preventDefault();
		dropzone.classList.add('dragover');
	});
	dropzone.addEventListener('dragleave', () => {
		dropzone.classList.remove('dragover');
	});
	dropzone.addEventListener('drop', (e) => {
		e.preventDefault();
		dropzone.classList.remove('dragover');
		const files = e.dataTransfer.files;
		if (files && files[0]) selectFile(files[0]);
	});
	// Click/keyboard open (only when background is clicked, not the label)
	dropzone.addEventListener('click', (e) => {
		if (e.target.closest('label.button')) return;
		fileInput.click();
	});
	dropzone.addEventListener('keydown', (e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			fileInput.click();
		}
	});

	fileInput.addEventListener('change', (e) => {
		if (e.target.files && e.target.files[0]) selectFile(e.target.files[0]);
	});

	summarizeBtn.addEventListener('click', async () => {
		if (!selectedFile) {
			setStatus('Please select a PDF or image first.', 'error');
			return;
		}
		setStatus('Uploading and processing…', 'info');
		setLoading(true);
		resultBox.classList.add('hidden');

		const form = new FormData();
		form.append('file', selectedFile);
		form.append('length', lengthSelect.value);

		try {
			const res = await fetch('/api/summarize', { method: 'POST', body: form });
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || 'Request failed');
			clearStatus();
			renderResult(data);
		} catch (err) {
			setStatus(err.message || 'Something went wrong', 'error');
		} finally {
			setLoading(false);
		}
	});

	function renderResult(data) {
		resultBox.classList.remove('hidden');
		summaryEl.textContent = data.summary || '';

		keypointsEl.innerHTML = '';
		(data.key_points || []).forEach((kp) => {
			const li = document.createElement('li');
			li.textContent = kp;
			keypointsEl.appendChild(li);
		});
	}
})();
