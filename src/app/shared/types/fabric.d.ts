// Fabric.js type augmentations for v5.3
declare module 'fabric' {
  export namespace fabric {
    class Canvas {
      constructor(element: HTMLCanvasElement | string, options?: any);
      add(...objects: FabricObject[]): Canvas;
      remove(...objects: FabricObject[]): Canvas;
      renderAll(): Canvas;
      getActiveObject(): FabricObject | null;
      getActiveObjects(): FabricObject[];
      setActiveObject(object: FabricObject): Canvas;
      discardActiveObject(): Canvas;
      bringToFront(object: FabricObject): Canvas;
      sendToBack(object: FabricObject): Canvas;
      dispose(): void;
      toDataURL(options?: any): string;
      getWidth(): number;
      getHeight(): number;
      backgroundColor: string | null;
      on(eventName: string, handler: Function): void;
      getElement(): HTMLCanvasElement;
    }

    class FabricObject {
      left?: number;
      top?: number;
      width?: number;
      height?: number;
      scaleX?: number;
      scaleY?: number;
      angle?: number;
      opacity?: number;
      fill?: string;
      stroke?: string;
      strokeWidth?: number;
      selectable?: boolean;
      evented?: boolean;
      clipPath?: FabricObject | null;
      set(options: any): FabricObject;
    }

    class Rect extends FabricObject {
      constructor(options?: any);
      rx?: number;
      ry?: number;
    }

    class IText extends FabricObject {
      constructor(text: string, options?: any);
      text: string;
      fontFamily?: string;
      fontSize?: number;
      fontWeight?: string;
      fontStyle?: string;
    }

    class Image extends FabricObject {
      static fromURL(url: string, callback: (img: Image) => void, options?: any): void;
    }

    class Shadow {
      constructor(options?: any);
      color?: string;
      blur?: number;
      offsetX?: number;
      offsetY?: number;
    }

    // Alias for backward compatibility
    type Object = FabricObject;
  }
}

