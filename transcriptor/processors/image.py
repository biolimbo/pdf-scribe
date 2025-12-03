"""
Image preprocessing module.

Provides various image enhancement techniques to improve OCR accuracy.
Each preprocessing mode targets specific document quality issues.
"""

from PIL import Image, ImageEnhance, ImageFilter

from transcriptor.config import PreprocessMode


class ImageProcessor:
    """
    Image preprocessing for OCR enhancement.

    Provides static methods for various preprocessing techniques that
    can be applied individually or in combination.
    """

    def __init__(self, binarize_threshold: int = 140):
        """
        Initialize the image processor.

        Args:
            binarize_threshold: Threshold for binarization (0-255)
                               Lower = more black, higher = more white
        """
        self.binarize_threshold = binarize_threshold

    def process(
        self,
        image: Image.Image,
        mode: PreprocessMode = PreprocessMode.NONE
    ) -> Image.Image:
        """
        Apply preprocessing based on the specified mode.

        Args:
            image: PIL Image to process
            mode: Preprocessing mode to apply

        Returns:
            Processed PIL Image
        """
        if mode == PreprocessMode.NONE:
            return image

        # Handle color highlight removal BEFORE grayscale conversion
        image = self._handle_color_channels(image, mode)

        if mode in (PreprocessMode.GRAYSCALE, PreprocessMode.REMOVE_RED,
                    PreprocessMode.REMOVE_BLUE):
            return image

        # Apply enhancements
        if mode in (PreprocessMode.CONTRAST, PreprocessMode.ALL,
                    PreprocessMode.CLEAN, PreprocessMode.SOFT):
            image = self.enhance_contrast(image)

        if mode in (PreprocessMode.SHARPEN, PreprocessMode.ALL,
                    PreprocessMode.CLEAN, PreprocessMode.SOFT):
            image = self.sharpen(image)

        if mode in (PreprocessMode.DENOISE, PreprocessMode.ALL,
                    PreprocessMode.CLEAN):
            # Skip denoise for "soft" mode
            image = self.denoise(image)

        if mode in (PreprocessMode.BINARIZE, PreprocessMode.ALL,
                    PreprocessMode.CLEAN):
            # Skip binarize for "soft" mode
            image = self.binarize(image)

        return image

    def _handle_color_channels(
        self,
        image: Image.Image,
        mode: PreprocessMode
    ) -> Image.Image:
        """
        Handle color channel extraction for highlight removal.

        For red highlights: use RED channel (red marks become white)
        For blue highlights: use BLUE channel (blue marks become white)

        Args:
            image: PIL Image (should be RGB)
            mode: Preprocessing mode

        Returns:
            Grayscale image (L mode)
        """
        if mode in (PreprocessMode.REMOVE_RED, PreprocessMode.CLEAN,
                    PreprocessMode.SOFT) and image.mode == "RGB":
            # Use red channel - red highlights appear white
            r, g, b = image.split()
            return r
        elif mode == PreprocessMode.REMOVE_BLUE and image.mode == "RGB":
            r, g, b = image.split()
            return b
        elif image.mode != "L":
            return image.convert("L")
        return image

    @staticmethod
    def to_grayscale(image: Image.Image) -> Image.Image:
        """Convert image to grayscale."""
        if image.mode != "L":
            return image.convert("L")
        return image

    @staticmethod
    def enhance_contrast(
        image: Image.Image,
        factor: float = 2.0
    ) -> Image.Image:
        """
        Enhance image contrast.

        Args:
            image: PIL Image
            factor: Contrast enhancement factor (1.0 = no change)

        Returns:
            Contrast-enhanced image
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    @staticmethod
    def sharpen(image: Image.Image) -> Image.Image:
        """Apply sharpening filter to enhance edges."""
        return image.filter(ImageFilter.SHARPEN)

    @staticmethod
    def denoise(image: Image.Image, size: int = 3) -> Image.Image:
        """
        Remove salt-and-pepper noise using median filter.

        Args:
            image: PIL Image
            size: Filter size (must be odd)

        Returns:
            Denoised image
        """
        return image.filter(ImageFilter.MedianFilter(size=size))

    def binarize(self, image: Image.Image) -> Image.Image:
        """
        Convert to black and white using threshold.

        Args:
            image: PIL Image (should be grayscale)

        Returns:
            Binarized image
        """
        threshold = self.binarize_threshold
        image = image.point(lambda x: 255 if x > threshold else 0, mode="1")
        return image.convert("L")  # Back to grayscale for compatibility

    def remove_red_highlights(self, image: Image.Image) -> Image.Image:
        """
        Remove red highlights by extracting the red channel.

        Red marks appear white in the red channel, while black text
        remains dark (low value in all channels).

        Args:
            image: RGB PIL Image

        Returns:
            Grayscale image with red marks removed
        """
        if image.mode != "RGB":
            return image.convert("L")
        r, g, b = image.split()
        return r

    def remove_blue_highlights(self, image: Image.Image) -> Image.Image:
        """
        Remove blue highlights by extracting the blue channel.

        Args:
            image: RGB PIL Image

        Returns:
            Grayscale image with blue marks removed
        """
        if image.mode != "RGB":
            return image.convert("L")
        r, g, b = image.split()
        return b
