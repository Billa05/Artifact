import { useState, useEffect } from "react"
import { Play, Pause, Download, AudioWaveformIcon as Waveform } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function TranscribePage() {
    const [text, setText] = useState("Enter the text you want to convert to speech using your cloned voice.")
    const [isPlaying, setIsPlaying] = useState(false)
    const [audioLength, setAudioLength] = useState(0)
    const [currentTime, setCurrentTime] = useState(0)
    const [pitch, setPitch] = useState(50)
    const [tone, setTone] = useState(50)
    const [clarity, setClarity] = useState(70)
    const [exportFormat, setExportFormat] = useState("mp3")
    const [selectedModel, setSelectedModel] = useState("voice-1")

    // Simulate audio wave generation based on text
    useEffect(() => {
        if (text) {
            // Calculate estimated audio length based on word count
            const wordCount = text.split(/\s+/).filter(Boolean).length
            const estimatedLength = Math.max(1, Math.min(180, wordCount * 0.5))
            setAudioLength(estimatedLength)
        } else {
            setAudioLength(0)
        }
    }, [text])

    // Simulate playback
    useEffect(() => {
        let interval: NodeJS.Timeout | null = null

        if (isPlaying && currentTime < audioLength) {
            interval = setInterval(() => {
                setCurrentTime((prev) => {
                    if (prev >= audioLength) {
                        setIsPlaying(false)
                        return audioLength
                    }
                    return prev + 0.1
                })
            }, 100)
        }

        return () => {
            if (interval) clearInterval(interval)
        }
    }, [isPlaying, currentTime, audioLength])

    const togglePlayback = () => {
        if (currentTime >= audioLength) {
            setCurrentTime(0)
        }
        setIsPlaying(!isPlaying)
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs < 10 ? "0" : ""}${secs}`
    }

    // Generate wave bars for visualization
    const waveBars = Array.from({ length: 120 }, (_, i) => {
        // Create a pattern that looks like a waveform
        const position = i / 120
        const progress = currentTime / audioLength

        // Different height calculation for played vs unplayed portions
        let height
        if (position <= progress) {
            // More dynamic heights for the played portion
            height = 10 + Math.sin(i * 0.2) * 15 + Math.cos(i * 0.3) * 10
        } else {
            // More subdued heights for the unplayed portion
            height = 5 + Math.sin(i * 0.2) * 7
        }

        return (
            <div
                key={i}
                className="wave-bar"
                style={{
                    height: `${height}px`,
                    left: `${i * 0.83}%`,
                    opacity: position <= progress ? 0.9 : 0.4,
                    backgroundColor: position <= progress ? undefined : "rgba(255, 255, 255, 0.3)",
                    width: "2px",
                    marginRight: "1px",
                }}
            />
        )
    })

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="flex flex-col gap-8">
                <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl">
                    <label className="text-sm font-medium text-gray-300 mb-3 block gradient-text">Voice Model</label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                        <SelectTrigger className="bg-gray-900/70 border-gray-700/50 h-12">
                            <SelectValue placeholder="Select a voice model" />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-900 border-gray-700">
                            <SelectItem value="voice-1">My Voice (Recorded Today)</SelectItem>
                            <SelectItem value="voice-2">Professional Voice</SelectItem>
                            <SelectItem value="voice-3">Casual Voice</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl flex-1">
                    <label className="text-sm font-medium text-gray-300 mb-3 block gradient-text">Text to Convert</label>
                    <Textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        className="h-64 bg-gray-900/70 border-gray-700/50 resize-none focus:ring-purple-500 text-base"
                        placeholder="Enter text to convert to speech..."
                    />
                </div>
            </div>

            <div className="flex flex-col gap-8">
                <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl">
                    <h3 className="text-sm font-medium mb-6 gradient-text">Voice Controls</h3>

                    <div className="space-y-8">
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <label className="text-gray-300 font-medium">Pitch</label>
                                <span className="text-gray-400 bg-gray-800/70 px-2 py-1 rounded-md text-xs">{pitch}%</span>
                            </div>
                            <Slider
                                value={[pitch]}
                                min={0}
                                max={100}
                                step={1}
                                onValueChange={(value) => setPitch(value[0])}
                                className="[&>span:first-child]:h-1.5 [&>span:first-child]:bg-gray-700"
                            />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <label className="text-gray-300 font-medium">Tone</label>
                                <span className="text-gray-400 bg-gray-800/70 px-2 py-1 rounded-md text-xs">{tone}%</span>
                            </div>
                            <Slider
                                value={[tone]}
                                min={0}
                                max={100}
                                step={1}
                                onValueChange={(value) => setTone(value[0])}
                                className="[&>span:first-child]:h-1.5 [&>span:first-child]:bg-gray-700"
                            />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <label className="text-gray-300 font-medium">Clarity</label>
                                <span className="text-gray-400 bg-gray-800/70 px-2 py-1 rounded-md text-xs">{clarity}%</span>
                            </div>
                            <Slider
                                value={[clarity]}
                                min={0}
                                max={100}
                                step={1}
                                onValueChange={(value) => setClarity(value[0])}
                                className="[&>span:first-child]:h-1.5 [&>span:first-child]:bg-gray-700"
                            />
                        </div>
                    </div>
                </div>

                <div className="glass-card rounded-2xl p-6 border border-gray-800/50 shadow-xl">
                    <div className="flex items-center gap-2 mb-4">
                        <Waveform className="h-4 w-4 text-blue-400" />
                        <h3 className="text-sm font-medium gradient-text">Audio Preview</h3>
                    </div>

                    <div className="flex justify-between text-xs text-gray-400 mb-2">
                        <span className="font-medium">{formatTime(currentTime)}</span>
                        <span>{formatTime(audioLength)}</span>
                    </div>

                    <div className="audio-wave mb-6 relative h-24">
                        {waveBars}
                        <div
                            className="absolute bottom-0 h-full bg-gradient-to-r from-blue-500/10 to-purple-500/10 pointer-events-none"
                            style={{ width: `${(currentTime / audioLength) * 100}%` }}
                        />
                    </div>

                    <div className="flex justify-between items-center">
                        <Button
                            onClick={togglePlayback}
                            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white border-0 shadow-lg shadow-blue-900/30"
                        >
                            {isPlaying ? (
                                <>
                                    <Pause className="mr-2 h-4 w-4" /> Pause
                                </>
                            ) : (
                                <>
                                    <Play className="mr-2 h-4 w-4" /> Play
                                </>
                            )}
                        </Button>

                        <div className="flex items-center gap-3">
                            <Select value={exportFormat} onValueChange={setExportFormat}>
                                <SelectTrigger className="w-28 h-10 bg-gray-800/70 border-gray-700/50">
                                    <SelectValue placeholder="Format" />
                                </SelectTrigger>
                                <SelectContent className="bg-gray-900 border-gray-700">
                                    <SelectItem value="mp3">MP3</SelectItem>
                                    <SelectItem value="wav">WAV</SelectItem>
                                    <SelectItem value="ogg">OGG</SelectItem>
                                    <SelectItem value="flac">FLAC</SelectItem>
                                </SelectContent>
                            </Select>

                            <Button className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white border-0 shadow-lg shadow-purple-900/30">
                                <Download className="mr-2 h-4 w-4" /> Export
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

