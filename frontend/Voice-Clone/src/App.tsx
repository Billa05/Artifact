import React, { useState } from 'react';
import { Mic, FileText } from 'react-feather';
import RecordPage from './components/voice';
import TranscribePage from './components/transcribe';

const App = () => {
  const [activePage, setActivePage] = useState("record");

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <header className="mb-12">
        <h1 className="text-3xl font-bold mb-8 text-center bg-gradient-to-r from-purple-500 via-fuchsia-500 to-blue-500 bg-clip-text text-transparent font-display">
          Voice Cloning Studio
        </h1>
        <nav className="flex justify-center gap-6 mb-8">
          <button
            className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${activePage === "record"
                ? "bg-gradient-to-r from-purple-900/40 to-blue-900/40 text-white border border-purple-700/50 shadow-lg shadow-purple-900/20"
                : "text-gray-400 hover:text-white hover:bg-gray-800/30"
              }`}
            onClick={() => setActivePage("record")}
          >
            <Mic size={18} className={activePage === "record" ? "text-purple-400" : ""} />
            <span className="font-medium">Record</span>
          </button>
          <button
            className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${activePage === "transcribe"
                ? "bg-gradient-to-r from-blue-900/40 to-purple-900/40 text-white border border-blue-700/50 shadow-lg shadow-blue-900/20"
                : "text-gray-400 hover:text-white hover:bg-gray-800/30"
              }`}
            onClick={() => setActivePage("transcribe")}
          >
            <FileText size={18} className={activePage === "transcribe" ? "text-blue-400" : ""} />
            <span className="font-medium">Transcribe</span>
          </button>
        </nav>
      </header>
      <main>
        {activePage === "record" && <RecordPage />}
        {activePage === "transcribe" && <TranscribePage />}
      </main>
    </div>
  );
};

export default App;