import * as ImagePicker from 'expo-image-picker';

export interface PickedImage {
  uri: string;
  mimeType: string;
  fileName: string;
}

function toPicked(asset: ImagePicker.ImagePickerAsset): PickedImage {
  const fallbackName = `screenshot-${Date.now()}.jpg`;
  return {
    uri: asset.uri,
    mimeType: asset.mimeType ?? 'image/jpeg',
    fileName: asset.fileName ?? fallbackName,
  };
}

/** Gallery selection; returns null when the user cancels or access fails. */
export async function pickImageFromGallery(): Promise<PickedImage | null> {
  try {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return null;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });
    if (result.canceled || result.assets === null || result.assets.length === 0) {
      return null;
    }
    const first = result.assets[0];
    if (first === undefined) return null;
    return toPicked(first);
  } catch {
    return null;
  }
}

/** Camera capture where the device supports it; null on cancel/failure. */
export async function captureImageWithCamera(): Promise<PickedImage | null> {
  try {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) return null;
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });
    if (result.canceled || result.assets === null || result.assets.length === 0) {
      return null;
    }
    const first = result.assets[0];
    if (first === undefined) return null;
    return toPicked(first);
  } catch {
    return null;
  }
}
