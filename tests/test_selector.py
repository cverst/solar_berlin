import filecmp
import unittest
import os
import shutil
import glob
import numpy as np
from PIL import Image


from selection.selection import DataSelector
from selection.errors import InvalidPathError, AbsolutePathError, OutputPathExistsError
from selection.errors import InvalidTileSizeError, InsuffientDataError

INPUT_PATH = os.path.join("data", "testing", "converted")
OUTPUT_PATH = os.path.join("data", "testing", "selected")

TILE_SIZES = (250, 500)
SELECTION_SIZES = ((10, 5), )
RANDOM_SEED = 42


class TestDataSelector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        # remove output from last run
        cls.clean_up()

        cls._first_run = True
        cls.selector = DataSelector(
            input_path=INPUT_PATH,
            testing=True,  # limit input to 32 tiles for faster testing
        )

        cls.selected_paths = []

        for selection_size in SELECTION_SIZES:
            for tile_size in TILE_SIZES:
                cls.selector.select_data(
                    tile_size=tile_size,
                    output_path=OUTPUT_PATH,
                    train_n=selection_size[0],
                    test_n=selection_size[1],
                    random_seed=RANDOM_SEED,
                )
                cls.selected_paths.append(os.path.join(
                    OUTPUT_PATH,
                    f"selected_tiles"
                    + f"_{tile_size}"
                    + f"_{selection_size[0]}"
                    + f"_{selection_size[1]}"
                    + f"_{RANDOM_SEED}"
                ))

    @staticmethod
    def clean_up():
        for tile_size in TILE_SIZES:
            tile_path = os.path.join(INPUT_PATH, f"tiled_{tile_size}")
            if os.path.exists(tile_path):
                shutil.rmtree(tile_path)
            for selection_size in SELECTION_SIZES:
                selection_path = os.path.join(
                    OUTPUT_PATH,
                    f"selected_tiles_"
                    + f"{tile_size}"
                    + f"_{selection_size[0]}"
                    + f"_{selection_size[1]}"
                    + f"_{RANDOM_SEED}"
                )
                if os.path.exists(selection_path):
                    shutil.rmtree(selection_path)

    def test_data_selector_creates_output_paths(self):
        for selected_path in self.selected_paths:
            self.assertTrue(os.path.exists(
                os.path.join(selected_path, "train")))
            self.assertTrue(os.path.exists(
                os.path.join(selected_path, "test")))

    def test_data_selector_selects_requested_number_of_images(self):
        for selected_path in self.selected_paths:
            for selection_size in SELECTION_SIZES:
                # count of train/test files is half the total due to map/msk
                train_files = os.listdir(os.path.join(selected_path, "train"))
                train_files_no = len(train_files) // 2
                test_files = os.listdir(os.path.join(selected_path, "test"))
                test_files_no = len(test_files) // 2
                self.assertEqual(train_files_no, selection_size[0])
                self.assertEqual(test_files_no, selection_size[1])

    def test_data_selector_refuses_to_overwrite_existing_directory(self):
        existing_path = os.path.join(
            OUTPUT_PATH,
            "existing_path"
        )
        with self.assertRaises(OutputPathExistsError):
            DataSelector(
                input_path=INPUT_PATH,
            ).select_data(
                tile_size=250,
                output_path=existing_path,
                train_n=10,
                test_n=5,
                random_seed=42,
            )

    def test_data_selector_throws_error_more_images_requested_than_exist(self):
        # huge train_n (only 32 tiles are available during testing)
        train_n = 10000
        test_n = 5
        tile_size = 500

        with self.assertRaises(InsuffientDataError):

            self.selector.select_data(
                tile_size=tile_size,
                train_n=train_n,
                test_n=test_n,
                output_path=OUTPUT_PATH,
                random_seed=42,
            )

    def test_data_selector_produces_expected_filenames(self):
        for selected_path in self.selected_paths:
            train_fns = os.listdir(os.path.join(selected_path, "train"))
            test_fns = os.listdir(os.path.join(selected_path, "test"))

            for image_fn in train_fns + test_fns:
                pattern_msk = "^.*-dop20[0-9_]*_msk.png$"
                pattern_map = "^.*-dop20[0-9_]*_map.png$"

                if "_map.png" in image_fn:
                    self.assertRegex(image_fn, pattern_map)
                else:
                    self.assertRegex(image_fn, pattern_msk)

    def test_data_selector_produces_expected_map_msk_split(self):
        for selected_path in self.selected_paths:
            train_files = os.listdir(os.path.join(selected_path, "train"))
            test_files = os.listdir(os.path.join(selected_path, "test"))

            map_count = 0
            msk_count = 0
            for image_fn in train_files + test_files:
                if "_map.png" in image_fn:
                    map_count += 1
                elif "_msk.png" in image_fn:
                    msk_count += 1

            self.assertEqual(map_count, msk_count)

    def test_data_selector_produces_expected_image_sizes(self):
        for selected_path in self.selected_paths:
            all_files = glob.glob(
                os.path.join(selected_path, "**", "*.png"),
                recursive=True,
            )

            tile_size = int(selected_path.split("_")[2])

            for image_fn in all_files:
                image = np.array(Image.open(image_fn))
                if "map" in image_fn:
                    self.assertEqual(image.shape, (tile_size, tile_size, 3))
                else:
                    self.assertEqual(image.shape, (tile_size, tile_size))

    def test_data_selector_raises_error_on_invalid_image_size_0(self):
        with self.assertRaises(InvalidTileSizeError):
            self.selector.select_data(0, 10, 5, OUTPUT_PATH, 42)

    def test_data_selector_raises_error_on_invalid_image_size_11k(self):
        with self.assertRaises(InvalidTileSizeError):
            self.selector.select_data(11_000, 10, 5, OUTPUT_PATH, 42)

    def test_data_selector_raises_error_on_invalid_image_size_224(self):
        with self.assertRaises(InvalidTileSizeError):
            # lossy is False by default, so this should fail
            self.selector.select_data(224, 10, 5, OUTPUT_PATH, 42)

    def test_data_selector_raises_error_on_invalid_input_path(self):
        with self.assertRaises(InvalidPathError):
            DataSelector(
                input_path="invalid_path",
            )

    def test_data_selector_raises_error_on_absolute_path(self):
        with self.assertRaises(AbsolutePathError):
            DataSelector(
                input_path=os.path.abspath(INPUT_PATH),
            )

    def test_data_selector_raises_error_on_empty_input_path(self):
        with self.assertRaises(InvalidPathError):
            DataSelector(
                input_path="",
            )

    def test_data_selector_raises_error_on_absolute_output_path(self):
        with self.assertRaises(AbsolutePathError):
            self.selector.select_data(
                500, 10, 5, output_path=os.path.abspath(OUTPUT_PATH),)

    def test_data_selector_produces_masks_with_expected_categories(self):
        all_msk_files = []
        for selected_path in self.selected_paths:
            all_msk_files += glob.glob(os.path.join(
                selected_path, "**", "*_msk.png"), recursive=True)
        msk_set = set()
        for msk_file in all_msk_files:
            msk_array = np.array(Image.open(msk_file))
            msk_set.update(msk_array.flatten())

        true_set = {0, 63, 127, 191, 255}
        self.assertSetEqual(msk_set, true_set)

    def test_data_selector_produces_expected_images(self):
        for selected_path in self.selected_paths:
            all_files_new = glob.glob(
                os.path.join(selected_path, "**", "*.png"),
                recursive=True,
            )

            all_files_known = glob.glob(
                os.path.join(selected_path + "_fixed", "**", "*.png"),
                recursive=True,
            )
        # check that all files are identical
        self.assertEqual(len(all_files_new), len(all_files_known))
        for i in range(len(all_files_new)):
            self.assertTrue(filecmp.cmp(all_files_new[i], all_files_known[i]))

    def test_data_selector_can_select_images_of_size_512(self):
        selected_path = os.path.join(OUTPUT_PATH, "selected_tiles_512_10_5_42")
        if os.path.exists(selected_path):
            shutil.rmtree(selected_path)
        self.selector.select_data(
            512,
            10,
            5,
            output_path=OUTPUT_PATH,
            random_seed=42,
            lossy=True,
        )
        images_selected = glob.glob(
            os.path.join(selected_path, "**", "*.png"),
            recursive=True,
        )
        self.assertEqual(len(images_selected), (10 + 5) * 2)

    def test_data_selector_picks_different_images_for_different_random_seeds(self):

        random_seeds = (43, 44)
        tile_size = 250
        train_n = 10
        test_n = 5

        selected_images = []

        for random_seed in random_seeds:
            selected_path = os.path.join(
                OUTPUT_PATH,
                f"selected_tiles_{tile_size}_{train_n}_{test_n}_{random_seed}"
            )
            if os.path.exists(selected_path):
                shutil.rmtree(selected_path)
            self.selector.select_data(
                tile_size=tile_size,
                train_n=train_n,
                test_n=test_n,
                output_path=OUTPUT_PATH,
                random_seed=random_seed,
            )
            selected_images.append(glob.glob(
                os.path.join(selected_path, "**", "*.png"),
                recursive=True,
            ))

        duplicates = set(selected_images[0]).intersection(selected_images[1])
        self.assertEqual(len(duplicates), 0)

    def test_data_selector_does_not_pick_same_images_in_test_and_train(self):
        for selected_path in self.selected_paths:
            train_fns = glob.glob(
                os.path.join(selected_path, "train", "**", "*.png"),
            )
            test_fns = glob.glob(
                os.path.join(selected_path, "test", "**", "*.png"),
            )

            for test_file in test_fns:
                self.assertNotIn(test_file, train_fns)

if __name__ == "__main__":
    unittest.main()