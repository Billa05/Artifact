import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Mic, FileText } from 'react-feather';
import RecordPage from './components/voice';
import TranscribePage from './components/transcribe';
import { VoiceProvider } from './context/VoiceContext';

// Navigation component with active state based on current route
function Navigation() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  const isTranscribe = location.pathname === "/transcribe";
  
  return (
    <header className="mb-12">
      <h1 className="text-3xl font-bold mb-8 text-center bg-gradient-to-r from-purple-500 via-fuchsia-500 to-blue-500 bg-clip-text text-transparent font-display">
        Voice Cloning Studio
      </h1>
      <nav className="flex justify-center gap-6 mb-8">
        <Link
          to="/"
          className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${
            isHome
              ? "bg-gradient-to-r from-purple-900/40 to-blue-900/40 text-white border border-purple-700/50 shadow-lg shadow-purple-900/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/30"
          }`}
        >
          <Mic size={18} className={isHome ? "text-purple-400" : ""} />
          <span className="font-medium">Record</span>
        </Link>
        <Link
          to="/transcribe"
          className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${
            isTranscribe
              ? "bg-gradient-to-r from-blue-900/40 to-purple-900/40 text-white border border-blue-700/50 shadow-lg shadow-blue-900/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/30"
          }`}
        >
          <FileText size={18} className={isTranscribe ? "text-blue-400" : ""} />
          <span className="font-medium">Transcribe</span>
        </Link>
      </nav>
    </header>
  );
}

const App = () => {
  return (
    <Router>
      <VoiceProvider>
        <div className="container mx-auto px-4 py-8 max-w-6xl">
          <Navigation />
          <main>
            <Routes>
              <Route path="/" element={<RecordPage />} />
              <Route path="/transcribe" element={<TranscribePage />} />
            </Routes>
          </main>
        </div>
      </VoiceProvider>
    </Router>
  );
};

export default App;