import React, { useState, useRef, useEffect } from 'react';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';
import { 
  FaBook, 
  FaVideo, 
  FaFilePowerpoint, 
  FaFileAlt, 
  FaTimes, 
  FaUpload, 
  FaFolderPlus 
} from 'react-icons/fa';
import './Upload.css';

const Upload = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLectureModalOpen, setIsLectureModalOpen] = useState(false);
  const [isPowerPointModalOpen, setIsPowerPointModalOpen] = useState(false);
  const [isNotesModalOpen, setIsNotesModalOpen] = useState(false);
  const [textbookFile, setTextbookFile] = useState(null);
  const [lectureFile, setLectureFile] = useState(null);
  const [powerPointFile, setPowerPointFile] = useState(null);
  const [notesFile, setNotesFile] = useState(null);
  const [pageRange, setPageRange] = useState('');
  const [lectureTitle, setLectureTitle] = useState('');
  const [powerPointTitle, setPowerPointTitle] = useState('');
  const [notesTitle, setNotesTitle] = useState('');
  const [isTextbook, setIsTextbook] = useState(true);
  const [tempPowerPointTitle, setTempPowerPointTitle] = useState('');
  const navigate = useNavigate();
  const notesInputRef = useRef(null);
  const powerPointInputRef = useRef(null);

  const handleFileChange = (event, type) => {
    const selectedFile = event.target.files[0];
    switch (type) {
      case 'textbook':
        setTextbookFile(selectedFile);
        break;
      case 'lecture':
        setLectureFile(selectedFile);
        break;
      case 'powerPoint':
        setPowerPointFile(selectedFile);
        break;
      case 'notes':
        setNotesFile(selectedFile);
        break;
      default:
        break;
    }
  };

  const handleSubmit = () => {
    console.log('File:', textbookFile);
    console.log('Page Range:', pageRange);
    setIsModalOpen(false);
  };

  const handleLectureSubmit = () => {
    console.log('Lecture Title:', lectureTitle);
    console.log('Lecture File:', lectureFile);
    setIsLectureModalOpen(false);
  };

  const handlePowerPointSubmit = () => {
    setPowerPointTitle(tempPowerPointTitle);
    setIsPowerPointModalOpen(false);
  };

  const handleNotesSubmit = () => {
    console.log('Notes Title:', notesTitle);
    console.log('Notes File:', notesFile);
    setIsNotesModalOpen(false);
  };

  // Modal component for reuse across different upload types.
  const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
      <div className="modal" onClick={onClose}>
        <div className="modal-content-new" onClick={e => e.stopPropagation()}>
          <div className="modal-header">
            <h2>{title}</h2>
            <button className="close-button" onClick={onClose}>
              <FaTimes size={20} />
            </button>
          </div>
          {children}
        </div>
      </div>
    );
  };

  useEffect(() => {
    if (isPowerPointModalOpen && powerPointInputRef.current) {
      powerPointInputRef.current.focus();
    }
  }, [isPowerPointModalOpen]);

  useEffect(() => {
    if (isNotesModalOpen && notesInputRef.current) {
      notesInputRef.current.focus();
    }
  }, [isNotesModalOpen]);

  return (
    <>
      <NavBar />
      <div className="upload-page">
        <h1 className="upload-title">Upload Your Materials</h1>
        <div className="upload-grid">
          <div className="upload-card" onClick={() => setIsModalOpen(true)}>
            <FaBook size={48} />
            <h3>Upload Textbook</h3>
          </div>
          <div className="upload-card" onClick={() => setIsLectureModalOpen(true)}>
            <FaVideo size={48} />
            <h3>Upload Lecture</h3>
          </div>
          <div className="upload-card" onClick={() => setIsPowerPointModalOpen(true)}>
            <FaFilePowerpoint size={48} />
            <h3>Upload PowerPoint</h3>
          </div>
          <div className="upload-card" onClick={() => setIsNotesModalOpen(true)}>
            <FaFileAlt size={48} />
            <h3>Upload Notes</h3>
          </div>
        </div>
        <div className="uploaded-files-container">
          <h2>Uploaded Files</h2>
          <ul>
            {textbookFile && <li>Textbook: {textbookFile.name}</li>}
            {lectureFile && <li>Lecture: {lectureFile.name}</li>}
            {powerPointFile && <li>PowerPoint: {powerPointFile.name}</li>}
            {notesFile && <li>Notes: {notesFile.name}</li>}
          </ul>
        </div>
        <button className="create-collection-btn">
          <FaFolderPlus className="btn-icon" size={20} />
          Create a collection
        </button>

        {/* Textbook Modal */}
        <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Upload Textbook">
          <div className="modal-form">
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  checked={isTextbook}
                  onChange={() => setIsTextbook(true)}
                />
                <span>Upload Textbook</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  checked={!isTextbook}
                  onChange={() => setIsTextbook(false)}
                />
                <span>Upload Non-Textbook PDFs</span>
              </label>
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Choose File</span>
                <input type="file" onChange={(e) => handleFileChange(e, 'textbook')} className="file-input" />
              </label>
              {textbookFile && <p className="file-name">{textbookFile.name}</p>}
            </div>
            {isTextbook && (
              <div className="input-group">
                <label>Table of Contents Page Range</label>
                <input
                  type="text"
                  value={pageRange}
                  onChange={(e) => setPageRange(e.target.value)}
                  placeholder="e.g., 1-10"
                  className="text-input"
                />
              </div>
            )}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* Lecture Modal */}
        <Modal isOpen={isLectureModalOpen} onClose={() => setIsLectureModalOpen(false)} title="Upload Lecture">
          <div className="modal-form">
            <div className="input-group">
              <label>Lecture Title</label>
              <input
                type="text"
                value={lectureTitle}
                onChange={(e) => setLectureTitle(e.target.value)}
                placeholder="Enter lecture title"
                className="text-input"
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload Media</span>
                <input type="file" onChange={(e) => handleFileChange(e, 'lecture')} className="file-input" />
              </label>
              {lectureFile && <p className="file-name">{lectureFile.name}</p>}
              <p className="file-type-hint">(.mp3, .mp4, .m4a, .wav files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsLectureModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleLectureSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* PowerPoint Modal */}
        <Modal isOpen={isPowerPointModalOpen} onClose={() => setIsPowerPointModalOpen(false)} title="Upload PowerPoint">
          <div className="modal-form">
            <div className="input-group">
              <label>PowerPoint Title</label>
              <input
                type="text"
                value={tempPowerPointTitle}
                onChange={(e) => setTempPowerPointTitle(e.target.value)}
                placeholder="Enter PowerPoint title"
                className="text-input"
                ref={powerPointInputRef}
                onFocus={() => powerPointInputRef.current.select()}
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload PowerPoint</span>
                <input type="file" onChange={(e) => handleFileChange(e, 'powerPoint')} className="file-input" />
              </label>
              {powerPointFile && <p className="file-name">{powerPointFile.name}</p>}
              <p className="file-type-hint">(.ppt, .pptx files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsPowerPointModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handlePowerPointSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* Notes Modal */}
        <Modal isOpen={isNotesModalOpen} onClose={() => setIsNotesModalOpen(false)} title="Upload Notes">
          <div className="modal-form">
            <div className="input-group">
              <label>Notes Title</label>
              <input
                type="text"
                value={notesTitle}
                onChange={(e) => setNotesTitle(e.target.value)}
                placeholder="Enter notes title"
                className="text-input"
                ref={notesInputRef}
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload Notes</span>
                <input type="file" onChange={(e) => handleFileChange(e, 'notes')} className="file-input" />
              </label>
              {notesFile && <p className="file-name">{notesFile.name}</p>}
              <p className="file-type-hint">(.jpg, .jpeg, .png files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsNotesModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleNotesSubmit}>Submit</button>
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
};

export default Upload;
