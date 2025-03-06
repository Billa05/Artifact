import React, { createContext, useState, useContext, ReactNode } from 'react';

interface VoiceContextProps {
    recordedAudio: Blob | null;
    refText: string;
    generatedAudio: Blob | null;
    isLoading: boolean;
    setRecordedAudio: (audio: Blob) => void;
    setRefText: (text: string) => void;
    setGeneratedAudio: (audio: Blob | null) => void;
    setIsLoading: (isLoading: boolean) => void;
    generateVoice: (genText: string) => Promise<void>;
}

const VoiceContext = createContext<VoiceContextProps | undefined>(undefined);

export function VoiceProvider({ children }: { children: ReactNode }) {
    const [recordedAudio, setRecordedAudio] = useState<Blob | null>(null);
    const [refText, setRefText] = useState<string>("");
    const [generatedAudio, setGeneratedAudio] = useState<Blob | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const generateVoice = async (genText: string) => {
        if (!recordedAudio || !refText) {
            console.error("Missing recorded audio or reference text");
            return;
        }

        setIsLoading(true);

        try {
            const formData = new FormData();
            formData.append('ref_file', recordedAudio, 'recording.wav');
            formData.append('ref_text', refText);
            formData.append('gen_text', genText);

            const response = await fetch('http://127.0.0.1:5000/generate', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const audioBlob = await response.blob();
            setGeneratedAudio(audioBlob);
        } catch (error) {
            console.error("Error generating voice:", error);
            alert("Failed to generate voice. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <VoiceContext.Provider
            value={{
                recordedAudio,
                refText,
                generatedAudio,
                isLoading,
                setRecordedAudio,
                setRefText,
                setGeneratedAudio,
                setIsLoading,
                generateVoice
            }}
        >
            {children}
        </VoiceContext.Provider>
    );
}

export function useVoiceContext() {
    const context = useContext(VoiceContext);
    if (context === undefined) {
        throw new Error('useVoiceContext must be used within a VoiceProvider');
    }
    return context;
}