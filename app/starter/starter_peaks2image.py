import copy

import numpy as np

from app.imports import *

import fabio.tifimage

import app.bokeh.app_peaks as app
from app.imports.clipboard import CrysalisPeaksCW

class Starter:

    OUTPUT_LINES = 10   # number of lines to limit output
    DEF_PALETTE = 'Greys256'
    INVERT_PALETTE = True

    DEF_PALETTES = ['Greys256', 'Inferno256', 'Magma256',
                     'Plasma256', 'Viridis256', 'Cividis256',
                     'Turbo256', 'Bokeh8', 'Spectral11', 'RdGy11', 'PiYG11']


    KEY_NEW   = "new"
    KEY_INDEX = "index"
    KEY_VALUE = "value"

    DEBUG = True

    # parameters for default values
    CAP_XOFFSET = 5
    CAP_YOFFSET = 5
    CAP_FONTSIZE = "1em"
    CAP_FONT = "Arial"
    CAP_COLOR = "rgba(255,255,255,1)"
    CAP_BKGCOLOR = "rgba(0,0,0,0.1)"
    CAP_VISIBLE = True
    SYM_TYPE = "circle"
    SYM_SIZE = 10
    SYM_LINECOLOR = "rgba(255,255,255,0.9)"
    SYM_LINESIZE = 2
    SYM_BKGCOLOR = "rgba(255,255,255,0)"
    SYM_VISIBLE = True

    IMG_ROTATION = "0"
    IMG_FLIP = "None"

    def __init__(self, *args, **kwargs):
        """
        Initialization
        """
        super(Starter, self).__init__()

        self._prep_parameters(*args, **kwargs)

        #if palette is not None and palette in self.DEF_PALETTES:
        #       self.DEF_PALETTE = palette

        # lock for the main class
        self.lock = threading.Lock()
        self.block_update = False
        self.last_filename = None

        # file upload
        self.lbl_filename = None
        self.btn_filename = None

        # graph controls
        self.btn_update = None
        self.btn_autoscale = None
        self.bgraph_controls = False
        self.cmb_palette = None
        self.cb_pallete = None

        self.range_intensity = None
        self.range_intensity_min = None
        self.range_intensity_max = None

        self.img_flip = None
        self.img_rotation = None

        # clipboard control
        self.btn_clipboard = None

        # caption controls
        self.cap_xoffset = None
        self.cap_yoffset = None
        self.cap_fontsize = None
        self.cap_font = None
        self.cap_color = None
        self.cap_bkgcolor = None
        self.cap_visible = None

        self.sym_type = None
        self.sym_size = None
        self.sym_linecolor = None
        self.sym_linesize = None
        self.sym_bkgcolor = None
        self.sym_visible = None

        self.acc_caption = None

        # output widget
        self.lbl_output = Output()
        self._output = []

        # last data loaded
        self.last_data = None
        self.last_image = None

        # filenames
        self.base_dir = os.path.dirname(__file__)
        self.tmp_dir = os.path.join(self.base_dir, "tmp")
        self.tmp_file = os.path.join(self.tmp_dir, "tmp.tif")

        # bokeh controller
        self.bc = None

        # point storage
        self.point_storage = []

        try:
            os.makedirs(self.tmp_dir)
        except (IOError, OSError):
            pass

        # init gui
        self._input_gui()
        self._init_bokeh()

        # peak watch dog
        self.crysalis_wdog = CrysalisPeaksCW(parent=self)

    def _prep_parameters(self, *args, **kwargs):
        """
        Prepares parameters passed as values
        :return:
        """
        klist = tuple(kwargs.keys())
        for k in klist:
            try:
                getattr(self, k.upper())

                v = kwargs[k]
                #if isinstance(v, str):
                #    v = v.lower()

                setattr(self, k.upper(), v)
            except AttributeError:
                pass

    def _input_gui(self):
        """
        Initializes the graphical design
        """
        # clipboard control
        self._init_clipboard()

        # file upload
        self._init_fileupload()

        # caption controls
        self._init_captioncontrols()

        #graph controls
        self._init_graphcontrols()


        # placing inside a layout
        display(self.lbl_filename)
        display(HBox([self.btn_filename, self.btn_update, self.btn_autoscale]))
        display(HBox([self.btn_clipboard, self.img_rotation, self.img_flip]))

        # controls of the caption
        display(self.acc_caption)

        # controls of the image
        display(HBox([self.cmb_palette, self.cb_pallete]))
        display(HBox([self.range_intensity]))

        # output for debuggine and etc
        display(self.lbl_output)

        asyncio.ensure_future(self._fn())


    def _init_fileupload(self):
        """
        Initializes file upload
        """
        # file upload button + label
        self.btn_filename = FileUpload(
            accept='.tif',  # Accepted file extension e.g. '.txt', '.pdf', 'image/*', 'image/*,.pdf'
            multiple=False,  # True to accept multiple files upload else False
            description='Load image file (*.tif) file:',
            layout=Layout(flex='0 1 auto', min_height='40px', width='200px'),
        )

        self.lbl_filename = HTML("")

    def _init_captioncontrols(self):
        """
        Initializes controls of captions and symbols
        :return:
        """
        # controls of the marker parameters
        mlist = ["circle", "square", "triangle", "cross"]

        v = self.SYM_TYPE.lower()
        if v not in mlist:
            self.SYM_TYPE = v = mlist[0]

        self.sym_type = mw1 = Dropdown(
            options=["circle", "square", "triangle", "cross"],
            value=self.SYM_TYPE,
            description="Symbol type:",
            layout=Layout(width="12em"),
            tooltip="Controls type of the symbols",
        )

        self.sym_size = mw2 = IntText(
            value=self.SYM_SIZE,
            description='Symbol size:',
            disabled=False,
            layout=Layout(width="12em"),
            tooltip="Controls size of symbols"
        )
        self.sym_linesize = mw3 = IntText(
            value=self.SYM_LINESIZE,
            description='Symbol line size:',
            disabled=False,
            layout=Layout(width="12em"),
            tooltip="Controls line size of symbols"
        )
        self.sym_linecolor = mw4 = Text(
            value=self.SYM_LINECOLOR,
            description="Line color:",
            layout=Layout(width="20em"),
            tooltip="Controls line color of the symbols",
        )
        self.sym_bkgcolor = mw5 = Text(
            value=self.SYM_BKGCOLOR,
            description="Fill color:",
            layout=Layout(width="20em"),
            tooltip="Controls fill color of the symbols",
        )

        self.sym_visible = mw6 = Checkbox(
            value=self.SYM_VISIBLE,
            description='Visibility:',
            disabled=False,
            tooltip="Controls visibility of the symbols",
        )

        # controls of the caption parameters
        self.cap_xoffset = cw1 = IntText(
            value=self.CAP_XOFFSET,
            description='X offset:',
            disabled=False,
            layout=Layout(width="10em"),
            tooltip="Controls X offset of the caption",
        )
        self.cap_yoffset = cw2 = IntText(
            value=self.CAP_YOFFSET,
            description='Y offset:',
            disabled=False,
            layout=Layout(width="10em"),
            tooltip="Controls Y offset of the caption",
        )
        self.cap_fontsize = cw3 = Text(
            value=self.CAP_FONTSIZE,
            description="Font size:",
            layout=Layout(width="12em"),
            tooltip="Controls fill color of the symbols",
        )
        flist = ["Arial", "Helvetica", "Tahoma", "Verdana", "Times New Roman"]

        if self.CAP_FONT not in flist:
            flist.insert(0, self.CAP_FONT)

        self.cap_font = cw4 = Dropdown(
            options=flist,
            value=flist[0],
            description="Text font:",
            layout=Layout(width="12em"),
            tooltip="Controls font of the symbols",
        )
        self.cap_color = cw5 = Text(
            value=self.CAP_COLOR,
            description="Text color:",
            layout=Layout(width="15em"),
            tooltip="Controls text color of the caption",
        )
        self.cap_bkgcolor = cw6 = Text(
            value=self.CAP_BKGCOLOR,
            description="Background color:",
            layout=Layout(width="15em"),
            tooltip="Controls background color of the caption",
        )
        self.cap_visible = cw7 = Checkbox(
            value=self.CAP_VISIBLE,
            description='Visibility:',
            disabled=False,
            tooltip="Controls visibility of the caption",
        )

        self.range_peakintensity = FloatSlider(
            value=0.,
            min=0.,
            max=1.,
            step=0.1,
            description='Peak intensity range:',
            disabled= True,
            continuous_update= False,
            orientation='horizontal',
            tooltip="Controls labeling of the peaks as filtered by value",
            readout=True,
            readout_format='.0f',
            layout=Layout(width='50%')
        )

        self.range_peakintensity.observe(self.action_default)

        self.acc_caption = accordion = Accordion(children=[
            HBox([self.range_peakintensity]),
            HBox([cw1, cw2, cw3, cw4, cw5, cw6, cw7]),
            HBox([mw1, mw2, mw3, mw4, mw5, mw6]),
        ])
        accordion.set_title(0, 'Filter caption intensity')
        accordion.set_title(1, 'Caption Style')
        accordion.set_title(2, 'Symbol Style')

    def _init_graphcontrols(self):
        """
        Initializes graph controls
        :return:
        """
        # display control
        self.cmb_palette = Dropdown(
            options=self.DEF_PALETTES,
            value=self.DEF_PALETTE,
            description='Color palette:',
            disabled=self.bgraph_controls,
            tooltip="Controls color palette of the image",
        )

        self.cmb_palette.observe(self.action_default)

        tlist = ['0', '90', '180', '270']
        v = self.IMG_ROTATION
        if isinstance(v, int) or isinstance(v, float):
            self.IMG_ROTATION = v = f"{v}"

        if v not in tlist:
            self.IMG_ROTATION = v = tlist[0]

        self.img_rotation = ToggleButtons(
            options=tlist,
            value=v,
            description='Image rotation:',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltips=['0 Degrees', '90 Degrees', '180 Degrees', '270 Degrees'],
            layout=Layout(display="flex", flex_flow="column", align_items='stretch')
        )
        self.img_rotation.style.button_width = '5em'
        self.img_rotation.observe(self.action_default)

        tlist = ['None', 'H', 'V']
        v = self.IMG_FLIP
        if len(v)==1:
            v = v.upper()
        if v not in tlist:
            v = tlist[0]

        self.img_flip = ToggleButtons(
            options=tlist,
            description='Image flip:',
            value=v,
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltips=['No flip', 'Flips image in vertical direction', 'Flips image in horizontal direction'],
            layout=Layout(display="flex", flex_flow="column", align_items='stretch')
        )
        self.img_flip.style.button_width = '5em'
        self.img_flip.observe(self.action_default)

        self.range_intensity = FloatRangeSlider(
            value=[0., 1.],
            min=0.,
            max=1.,
            step=0.1,
            description='Data Range:',
            disabled= True, #not self.bgraph_controls,
            continuous_update=False,
            orientation='horizontal',
            tooltip="Controls intesity scale of the image",
            readout=True,
            readout_format='.2f',
            layout=Layout(width='50%')
        )

        self.range_intensity.observe(self.action_intensity, 'value')

        self.btn_update = Button(description="Update",
                                 disabled=True,
                                 tooltip="Updates the graph without reloading the file",
                                 layout=Layout(flex='0 1 auto', min_height='40px', width='200px')
                                 )
        self.btn_update.on_click(self.reload_graph)

        self.btn_autoscale = Button(description="Autoscale",
                                 disabled=True,
                                 tooltip="Autoscales the graph",
                                 layout=Layout(flex='0 1 auto', min_height='40px', width='200px')
                                 )
        self.btn_autoscale.on_click(self.action_autoscale)

        self.cb_pallete = Checkbox(
            value=self.INVERT_PALETTE,
            description='Invert the pallete',
            disabled=False,
            tooltip="Controls inversion of the color palette",
        )

        self.cb_pallete.observe(self.action_default)


    def _init_clipboard(self):
        """
        Initializes interface for a clipboard
        :return:
        """
        tlist = ["On", "Off"]
        self.btn_clipboard = ToggleButtons(
            options=tlist,
            value=tlist[-1],
            description='Clipboard polling:',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltips=['Switches clipboard polling on', 'Switches clipboard polling off'],
            layout=Layout(display="flex", flex_flow="column", align_items='stretch')
        )
        self.btn_clipboard.style.button_width = '5em'
        self.btn_clipboard.observe(self.action_clipboardpolling)

    def action_autoscale(self, *args, **kwargs):
        """
        Autoscales the graph using the mean value
        :return:
        """
        if self.last_image is not None:
            data = self.last_image.data
            avrg = np.average(data)
            mi, ma = self.range_intensity.min, self.range_intensity.max
            tvi, tva = 0, 3*avrg
            tvi, tva = max(mi, tvi), min(tva,ma)
            self.range_intensity.value = [tvi, tva]

            # self.reload_graph()

    def action_intensity(self, change):
        """
        Action processing changes of the intensity range scale
        :param change:
        :return:
        """
        # self.debug(f"Value changed: {change[self.KEY_NEW]}")

        if self.block_update:
            return

        if self.last_image is not None:
            (self.range_intensity_min, self.range_intensity_max) = change[self.KEY_NEW]
            self.reload_graph()

    def action_default(self, change):
        """
        Default implementation of an action
        :param change:
        :return:
        """
        # self.debug(f"Value changed: {change[self.KEY_NEW]}")
        test = isinstance(change[self.KEY_NEW], dict) and not self.KEY_INDEX in change[self.KEY_NEW]

        if self.last_image is not None and test:
            self.reload_graph()

    def action_clipboardpolling(self, change):
        """
        Controls clipboard polling
        :return:
        """
        # self.debug(f"Value changed: {change[self.KEY_NEW]}")
        test = isinstance(change[self.KEY_NEW], dict) and not self.KEY_INDEX in change[self.KEY_NEW]

        if test:
            v = self.btn_clipboard.value
            if v.lower() == "on":
                self.crysalis_wdog.start_polling()
            else:
                self.crysalis_wdog.stop_polling()

    def _init_bokeh(self):
        """
        Initializes bokeh application
        :return:
        """
        self.bc = app.BokehCtrl.get_instance()
        self.bc.parent = self
        # self.debug(f"Init bokeh controller {self.bc}")

    def _enable_graph_controls(self, bflag):
        """
        Disables or enables graph controls
        :param bflag:
        :return:
        """
        for el in (self.range_intensity, self.btn_update, self.btn_autoscale):
            if el is not None:
                self.bgraph_controls = bflag
                el.disabled = not bflag

    def test_graphcontrols(self):
        """
        Tests the state of controls
        :return:
        """
        res = True
        for el in (self.range_intensity, self.btn_update, self.btn_autoscale):
            if el is not None:
                if el.disabled:
                    res = not el.disabled
                    break
        return res

    def wait_for_filename_change(self, widget, value):
        """
        Processes asynch data change based on a widget
        """
        future = asyncio.Future()

        def update(change):
            future.set_result(change.new)

            fn = ""
            tdata = None

            if isinstance(change.new, dict):
                fn = tuple(change.new.keys())[0]
                tdata = change.new
            elif isinstance(change.new, list) or isinstance(change.new, tuple):
                fn = tuple(change.new[0].keys())[0]
                tdata = change.new[0]
            self.last_data = tdata

            # process data separately
            th = threading.Thread(target=self.process_newfile, args=[fn, tdata])
            th.setDaemon(True)
            th.start()

            widget.unobserve(update, value)

        widget.observe(update, value)
        return future

    async def _fn(self):
        """
        Async handling of the uploaded file change
        """

        while True:
            x = await self.wait_for_filename_change(self.btn_filename, 'value')

    def process_newfile(self, fn, data):
        """
        Processes filename change and the data content
        :param fn:
        :param data:
        :return:
        """

        with open(self.tmp_file, "wb") as fh:
            fh.write(data['content'])

        #self.debug(f"Writing a temporary file {self.tmp_file}")

        # tif = fabio.tifimage.TifImage()
        with fabio.openimage.openimage(self.tmp_file) as fh:
            img_data = fh.data

        #img_data = tif.read(self.tmp_file)

        ave = np.average(img_data.data)

        test_ave = np.copy(img_data)
        test_ave[test_ave > ave] = 0
        test_ave = np.average(test_ave)

        mi, ma = np.min(img_data.data), np.max(img_data.data)


        palette = self.DEF_PALETTE
        binvert_colormap = self.cb_pallete.value

        self.block_update = True
        with self.lock:
            self.last_image = img_data

            self.last_filename = fn
            self.lbl_filename.value = f"""
                <div>Filename: {fn}</div><div>Image dimensions: {img_data.shape}</div>
                <div>Min: {mi}; Max: {ma}; Average: {ave};</div>
                """

            if not self.test_graphcontrols():
                self._enable_graph_controls(True)

            # update range intensity
            if isinstance(self.range_intensity, FloatRangeSlider):
                self.range_intensity.min, self.range_intensity.max = mi, test_ave * 10

                if self.range_intensity_min is None or self.range_intensity_min<mi:
                    self.range_intensity_min = mi

                if self.range_intensity_max is None or self.range_intensity_max > ave:
                    self.range_intensity_max = test_ave * 10

                self.range_intensity.value = [self.range_intensity_min, self.range_intensity_max]

            if isinstance(self.cmb_palette, Dropdown):
                palette = self.cmb_palette.value

        #self.debug(f"Bokeh controller is {self.bc}")
        if self.bc is not None:
            #self.debug("Starting")
            #self.bc.add_graph(img_data.data, palette, self.range_intensity_min, self.range_intensity_max)
            self.reload_graph()
            #self.debug(f"Data added {img_data.data}")

            #self.debug(f"Loaded file: {fn};")

        self.block_update = False

    def reload_graph(self,*args, **kwargs):
        """
        Processes the values set by interface and update the image
        :return:
        """
        img_data = None
        palette = self.DEF_PALETTE
        imin, imax = None, None
        binvert_colormap = None
        filter_captions = None

        with self.lock:
            img_data = self.last_image.data
            palette = self.cmb_palette.value
            imin, imax = self.range_intensity_min, self.range_intensity_max
            binvert_colormap = self.cb_pallete.value
            filter_captions = self.range_peakintensity.value

        # adjusting rotation
        rotation = int(self.img_rotation.value)
        if rotation > 0:
            img_data = np.rot90(img_data, k=int(rotation/90.))

        # flipping the dataif necessary
        flip = self.img_flip.value
        if "v" in flip.lower():
            img_data = np.flipud(img_data)
        elif "h" in flip.lower():
            img_data = np.fliplr(img_data)

        #self.debug(f"Rotation: {rotation}; Flip: {flip}")

        if self.bc is not None:
            # show points if there is data to show
            if len(self.point_storage) > 0:
                # collect data from caption and symbol styles
                sym_data = (self.sym_type.value, self.sym_size.value, self.sym_linesize.value, self.sym_linecolor.value, self.sym_bkgcolor.value,
                            self.sym_visible.value)

                self.bc.set_symbol_style(*sym_data)

                cap_data = (
                self.cap_xoffset.value, self.cap_yoffset.value, self.cap_font.value, self.cap_fontsize.value,
                self.cap_color.value, self.cap_bkgcolor.value, self.cap_visible.value)

                self.bc.set_caption_style(*cap_data)
                self.bc.points = self.point_storage

                self.bc.filter_captions = filter_captions
            else:
                self.bc.points = []

            #self.debug("Sending data into a graph")
            #self.debug(f"Data added {img_data.shape}")
            #self.debug(f"Palette: {palette}")
            #self.debug(f"Min/Max: {imin}/{imax}")
            #self.debug(f"Colormap inversion: {binvert_colormap}")

            self.bc.add_graph(np.copy(img_data), palette, imin, imax, binvert_colormap)

    def debug(self, msg):
        """
        Simple debugging working through the output widget
        :param msg:
        :return:
        """
        if not self.DEBUG:
            return

        if self.lbl_output is None:
            self.lbl_output = Output()
            display(self.lbl_output)    # kind of issue in jupyter+asyncio - it is safer to declare upon start

        self._output.append(msg)
        if len(self._output) > self.OUTPUT_LINES:
            self._output.pop(0)

        self.clear_output_widget(self.lbl_output)
        for tmsg in self._output:
            self.lbl_output.append_stdout(tmsg+"\n")

    def clear_output_widget(self, widget):
        """
        Clears output - jupyter operation is buggy
        :return:
        """
        widget.outputs = ()

    def process_cbdata(self, data):
        """
        Processes data from the clipboard
        :param data:
        :return:
        """
        data, min_value, max_value = data

        min_value, max_value = min(min_value, max_value), max(min_value, max_value)

        if min_value == max_value:
            max_value = min_value + 1.

        # self.debug(f"Got data {(len(data), min_value, max_value)}")

        if isinstance(data, list) or isinstance(data, tuple):
            self.point_storage = copy.deepcopy(data)
            # show the control when the data arrives

            if isinstance(self.range_peakintensity, FloatSlider):

                tnew_value = told_value = self.range_peakintensity.value
                self.range_peakintensity.min = -1.
                self.range_peakintensity.max = max_value
                self.range_peakintensity.min = min_value

                if told_value < min_value:
                    tnew_value = min_value
                if told_value > max_value:
                    tnew_value = max_value

                if self.range_peakintensity.disabled:
                    self.range_peakintensity.disabled = False
                    tnew_value = min_value

                self.range_peakintensity.value = tnew_value

            if self.last_image is not None:
                self.reload_graph()
