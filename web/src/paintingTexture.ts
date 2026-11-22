import * as THREE from "three";

/** A painting's texture. The image is fetched and decoded off the main thread
 * (ImageBitmapLoader), flipped as it is decoded since WebGL ignores Texture.flipY for an
 * ImageBitmap: its rows go up the GPU in the order TextureLoader's flipY sent them. With a
 * renderer, each texture is uploaded as soon as its image is in, while the hall is still loading,
 * rather than in the hall's first frame. Scene.tsx hangs it and Banners.tsx crops two of the
 * images (texture.image); both load through this class, so each image is fetched, decoded and
 * uploaded once (useLoader caches by loader and URL). */
export class PaintingTextureLoader extends THREE.Loader<THREE.Texture> {
  renderer: THREE.WebGLRenderer | null = null;
  private images = new THREE.ImageBitmapLoader(this.manager).setOptions({ imageOrientation: "flipY", premultiplyAlpha: "none" });

  override load(url: string, onLoad: (t: THREE.Texture) => void, onProgress?: (e: ProgressEvent) => void, onError?: (e: unknown) => void) {
    this.images.load(url, (image) => {
      const t = new THREE.Texture(image);
      t.flipY = false;
      t.colorSpace = THREE.SRGBColorSpace;
      t.needsUpdate = true;
      if (this.renderer) {
        t.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
        this.renderer.initTexture(t);
      }
      onLoad(t);
    }, onProgress, onError);
  }
}
