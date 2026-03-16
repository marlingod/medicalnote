"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Camera, Upload, X } from "lucide-react";

interface ScanUploadProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
}

export function ScanUpload({ onUpload, isUploading }: ScanUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      return;
    }
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleUpload = () => {
    if (selectedFile) onUpload(selectedFile);
  };

  const clearSelection = () => {
    setPreview(null);
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <Card>
      <CardContent className="py-6 space-y-4">
        {!preview ? (
          <div
            className="border-2 border-dashed rounded-lg p-12 text-center cursor-pointer hover:border-primary transition-colors"
            onClick={() => inputRef.current?.click()}
          >
            <Camera className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="font-medium">Upload a scanned document or photo</p>
            <p className="text-sm text-muted-foreground mt-1">
              Supports JPG, PNG, PDF. Max 10MB.
            </p>
            <input
              ref={inputRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="relative">
              <img src={preview} alt="Scan preview" className="max-h-64 mx-auto rounded-lg" />
              <Button
                variant="destructive"
                size="icon"
                className="absolute top-2 right-2"
                onClick={clearSelection}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <Button onClick={handleUpload} disabled={isUploading} className="w-full">
              <Upload className="mr-2 h-4 w-4" />
              {isUploading ? "Processing..." : "Process Scan"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
