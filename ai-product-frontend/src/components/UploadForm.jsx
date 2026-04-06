import { useState } from "react";
import { uploadImage } from "../api/searchApi";

export default function UploadForm() {
  const [file, setFile] = useState(null);

  const handleSubmit = async () => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_id", "U123");

    const res = await uploadImage(formData);
    console.log(res.data);
  };

  return (
    <div>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleSubmit}>Upload</button>
    </div>
  );
}
