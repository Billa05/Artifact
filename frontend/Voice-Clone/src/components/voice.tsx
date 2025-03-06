import { useState, useEffect, useRef } from "react"
import { Play, Pause, SkipBack, Settings, Loader, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Add context API for sharing state between components
import { useVoiceContext } from "../context/VoiceContext.tsx"

export default function RecordPage() {
    const [isRecording, setIsRecording] = useState(false)
    const [isPaused, setIsPaused] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const [currentWordIndex, setCurrentWordIndex] = useState(0)
    const [scrollSpeed, setScrollSpeed] = useState(1)
    const [isProcessing, setIsProcessing] = useState(false)
    const [audioLevel, setAudioLevel] = useState(0)
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [uploadedAudioUrl, setUploadedAudioUrl] = useState<string | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    
    const navigate = useNavigate();
    // Add to store the recorded audio blob
    const { setRecordedAudio, setRefText } = useVoiceContext()

    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const audioContextRef = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)
    const mediaStreamRef = useRef<MediaStream | null>(null)
    const animationFrameRef = useRef<number | null>(null)
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const audioChunksRef = useRef<Blob[]>([])
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    const sampleText = "I'm absolutely furious that you shared our private conversation with everyone in the office after promising to keep it confidential!"
    const words = sampleText.split(" ")

    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
            }
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current)
            }
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach((track) => track.stop())
            }
            if (uploadedAudioUrl) {
                URL.revokeObjectURL(uploadedAudioUrl)
            }
        }
    }, [uploadedAudioUrl])

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            mediaStreamRef.current = stream

            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
            audioContextRef.current = audioContext

            const analyser = audioContext.createAnalyser()
            analyserRef.current = analyser
            analyser.fftSize = 256

            const source = audioContext.createMediaStreamSource(stream)
            source.connect(analyser)

            const dataArray = new Uint8Array(analyser.frequencyBinCount)

            // Create MediaRecorder to actually record the audio
            const mediaRecorder = new MediaRecorder(stream)
            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunksRef.current.push(event.data)
            })

            mediaRecorder.start()

            const updateAudioLevel = () => {
                if (analyserRef.current) {
                    analyserRef.current.getByteFrequencyData(dataArray)
                    const average = dataArray.reduce((acc, val) => acc + val, 0) / dataArray.length
                    setAudioLevel(average / 128) // Normalize to 0-1 range
                    animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
                }
            }

            updateAudioLevel()

            setIsRecording(true)
            setIsPaused(false)

            timerRef.current = setInterval(() => {
                setRecordingTime((prev) => prev + 1)

                // Auto-advance the teleprompter
                if (!isPaused) {
                    setCurrentWordIndex((prev) => {
                        if (prev < words.length - 1) {
                            return prev + (1 * scrollSpeed) / 2
                        }
                        return prev
                    })
                }
            }, 1000)
        } catch (err) {
            console.error("Error accessing microphone:", err)
        }
    }

    const pauseRecording = () => {
        setIsPaused(true)
        if (timerRef.current) {
            clearInterval(timerRef.current)
        }
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.pause()
        }
    }

    const resumeRecording = () => {
        setIsPaused(false)
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
            mediaRecorderRef.current.resume()
        }

        timerRef.current = setInterval(() => {
            setRecordingTime((prev) => prev + 1)

            // Auto-advance the teleprompter
            setCurrentWordIndex((prev) => {
                if (prev < words.length - 1) {
                    return prev + (1 * scrollSpeed) / 2
                }
                return prev
            })
        }, 1000)
    }

    const stopRecording = () => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
        }
        if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current)
        }

        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop()
        }

        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((track) => track.stop())
        }

        setIsRecording(false)
        setIsPaused(false)
        setCurrentWordIndex(0)
        setRecordingTime(0)
        setAudioLevel(0)
    }

    const processRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();

            mediaRecorderRef.current.addEventListener('stop', () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                setRecordedAudio(audioBlob);
                setRefText(sampleText);

                stopRecording();
                setIsProcessing(true);

                // Navigate to transcribe page after delay
                setTimeout(() => {
                    setIsProcessing(false);
                    navigate('/transcribe');
                }, 1000);
            });
        } else {
            // If recording was already stopped
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
            setRecordedAudio(audioBlob);
            setRefText(sampleText);

            setIsProcessing(true);
            setTimeout(() => {
                setIsProcessing(false);
                navigate('/transcribe');
            }, 1000);
        }
    }

    // New functions for file upload functionality
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file && file.type.startsWith('audio/')) {
            setUploadedFile(file);
            
            // Create URL for the audio preview
            if (uploadedAudioUrl) {
                URL.revokeObjectURL(uploadedAudioUrl);
            }
            const url = URL.createObjectURL(file);
            setUploadedAudioUrl(url);
        }
    };

    const triggerFileInput = () => {
        fileInputRef.current?.click();
    };

    const processUploadedFile = () => {
        if (uploadedFile) {
            setIsUploading(true);
            
            // Convert the File to Blob and store it in the context
            uploadedFile.arrayBuffer().then(arrayBuffer => {
                const blob = new Blob([arrayBuffer], { type: uploadedFile.type });
                setRecordedAudio(blob);
                
                // Since we don't have actual transcription, we'll use a placeholder
                // In a real app, you might want to let the user input the reference text
                const uploadRefText = "This is reference audio for voice cloning. Please use this sample to generate voice with my tone and speaking style.";
                setRefText(uploadRefText);
                
                setTimeout(() => {
                    setIsUploading(false);
                    navigate('/transcribe');
                }, 1000);
            });
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs < 10 ? "0" : ""}${secs}`
    }

    // Generate wave bars for visualization
    const waveBars = Array.from({ length: 60 }, (_, i) => {
        const height = isRecording
            ? 10 + Math.sin(i * 0.2 + Date.now() * 0.005) * 20 + Math.random() * 30 * audioLevel
            : 5 + Math.sin(i * 0.3) * 3

        return (
            <div
                key={i}
                className="wave-bar"
                style={{
                    height: `${height}px`,
                    left: `${i * 1.67}%`,
                    transition: "height 0.1s ease",
                    opacity: isRecording ? 0.7 + Math.random() * 0.3 : 0.4,
                }}
            />
        )
    })

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="flex flex-col">
                <div className="glass-card rounded-2xl p-8 h-[450px] overflow-auto shadow-xl relative">
                    <div className="absolute top-0 left-0 w-full h-16 bg-gradient-to-b from-gray-900/90 to-transparent z-10 pointer-events-none"></div>
                    <div className="absolute bottom-0 left-0 w-full h-16 bg-gradient-to-t from-gray-900/90 to-transparent z-10 pointer-events-none"></div>
                    <div className="teleprompter-text text-lg font-light leading-relaxed">
                        {words.map((word, index) => (
                            <span key={index} className={index === Math.floor(currentWordIndex) ? "current" : "other"}>
                                {word}{" "}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-8">
                <Tabs defaultValue="record" className="w-full">
                    <TabsList className="grid w-full grid-cols-2 mb-6">
                        <TabsTrigger value="record">Record Audio</TabsTrigger>
                        <TabsTrigger value="upload">Upload Audio</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="record">
                        <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl">
                            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center">
                                <span
                                    className={`inline-block w-2 h-2 rounded-full mr-2 ${isRecording ? "bg-red-500 pulse-animation" : "bg-gray-500"}`}
                                ></span>
                                Audio Recording
                            </h3>

                            <div className="audio-wave mb-3">
                                <div className="optimal-level" />
                                {waveBars}
                            </div>

                            <div className="flex justify-between text-xs text-gray-400 mt-3">
                                <span className="font-medium">{formatTime(recordingTime)}</span>
                                <span
                                    className={`${audioLevel > 0.7 ? "text-green-400" : audioLevel > 0.3 ? "text-yellow-400" : "text-gray-400"}`}
                                >
                                    Level: {Math.round(audioLevel * 100)}%
                                </span>
                            </div>
                        </div>

                        <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl mt-6">
                            <h3 className="text-sm font-medium text-gray-300 mb-5 flex items-center">
                                <span className="gradient-text">Recording Controls</span>
                            </h3>

                            <div className="flex items-center justify-between gap-4 mb-4">
                                <div className="flex gap-3">
                                    {!isRecording ? (
                                        <Button
                                            onClick={startRecording}
                                            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white border-0 shadow-lg shadow-purple-900/30"
                                        >
                                            <Play className="mr-2 h-4 w-4" /> Start
                                        </Button>
                                    ) : (
                                        <>
                                            <Button onClick={stopRecording} variant="destructive" className="shadow-lg shadow-red-900/30">
                                                <SkipBack className="mr-2 h-4 w-4" /> Stop
                                            </Button>

                                            {isPaused ? (
                                                <Button
                                                    onClick={resumeRecording}
                                                    className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white border-0 shadow-lg shadow-green-900/30"
                                                >
                                                    <Play className="mr-2 h-4 w-4" /> Resume
                                                </Button>
                                            ) : (
                                                <Button
                                                    onClick={pauseRecording}
                                                    variant="outline"
                                                    className="border-gray-700 bg-gray-800/50 hover:bg-gray-800 text-gray-200"
                                                >
                                                    <Pause className="mr-2 h-4 w-4" /> Pause
                                                </Button>
                                            )}
                                        </>
                                    )}
                                </div>

                                <div className="flex items-center gap-3 bg-gray-900/50 px-3 py-2 rounded-lg">
                                    <span className="text-xs text-gray-300 font-medium">Speed:</span>
                                    <Slider
                                        value={[scrollSpeed]}
                                        min={0.5}
                                        max={2}
                                        step={0.1}
                                        onValueChange={(value) => setScrollSpeed(value[0])}
                                        className="w-40 [&>span:first-child]:h-1.5 [&>span:first-child]:bg-gray-700"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-center mt-6">
                            <Button
                                onClick={processRecording}
                                className={`rounded-full w-20 h-20 ${isProcessing ? "bg-gray-700" : "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"} shadow-xl shadow-purple-900/20 transition-all duration-300 ${isRecording && !isProcessing ? "scale-105 glow-effect" : "opacity-70"}`}
                                disabled={!isRecording || isProcessing}
                            >
                                {isProcessing ? <Loader className="h-6 w-6 animate-spin" /> : <span className="font-medium">Process</span>}
                            </Button>
                        </div>
                    </TabsContent>

                    <TabsContent value="upload">
                        <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl">
                            <h3 className="text-sm font-medium text-gray-300 mb-5 flex items-center">
                                <span className="gradient-text">Upload Audio File</span>
                            </h3>
                            
                            <div className="flex flex-col items-center justify-center p-10 border-2 border-dashed border-gray-700 rounded-xl bg-gray-900/30 mb-6">
                                <input 
                                    ref={fileInputRef}
                                    type="file" 
                                    accept="audio/*" 
                                    className="hidden"
                                    onChange={handleFileChange}
                                />
                                
                                <Upload className="w-12 h-12 text-gray-400 mb-4" />
                                
                                {uploadedFile ? (
                                    <div className="text-center">
                                        <p className="text-green-400 font-medium mb-2">{uploadedFile.name}</p>
                                        <p className="text-xs text-gray-400 mb-4">
                                            {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                                        </p>
                                        <audio ref={audioRef} src={uploadedAudioUrl || ''} controls className="w-full mb-4" />
                                        <Button 
                                            variant="outline"
                                            onClick={triggerFileInput}
                                            className="border-gray-700 text-gray-300"
                                        >
                                            Replace File
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="text-center">
                                        <p className="text-gray-300 font-medium mb-2">Drop audio file here</p>
                                        <p className="text-xs text-gray-400 mb-4">or</p>
                                        <Button 
                                            variant="outline"
                                            onClick={triggerFileInput}
                                            className="border-gray-700 text-gray-300"
                                        >
                                            Browse Files
                                        </Button>
                                    </div>
                                )}
                            </div>
                            
                            <div className="text-xs text-gray-400 mb-6">
                                <p>Supported formats: WAV, MP3, AAC, FLAC</p>
                                <p>For best results, use a high-quality recording with clear speech</p>
                            </div>
                            
                            <Button 
                                onClick={processUploadedFile}
                                disabled={!uploadedFile || isUploading}
                                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                            >
                                {isUploading ? (
                                    <>
                                        <Loader className="mr-2 h-4 w-4 animate-spin" /> Processing...
                                    </>
                                ) : (
                                    'Continue with Uploaded Audio'
                                )}
                            </Button>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    )
}