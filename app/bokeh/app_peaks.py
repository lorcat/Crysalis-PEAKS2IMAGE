from app.imports import *

from bokeh.layouts import column, row
import bokeh.palettes as palettes
from bokeh.models import ColumnDataSource, Div, LinearColorMapper, LabelSet, Range1d, LinearAxis

from bokeh.plotting import figure, show

from tornado import gen
from functools import partial

from app.imports.clipboard import CrysalisPeak

__all__ = ["BokehCtrl", "show", "bokeh_app"]

BOKEHCTRL = None

def bokeh_app(doc):
    """
    Sets up bokeh server in combination with Jupyter
    :param doc:
    :return:
    """
    bc = BokehCtrl.get_instance()

    bc.document = doc

    layout = column(row(Div(text=f"Bokeh placeholder for document {str(bc.document)}", width=600, height=40), name=bc.NAME_DATA), name=bc.MAIN_LAYOUT)

    doc.add_root(layout)

class BokehCtrl:
    """
    Bokeh controller serving as a middle agent, accessible through different code parts
    """

    MAIN_LAYOUT = "main_layout"
    MAIN_PALLETE = "Spectral11"

    NAME_DATA = "data"

    def __init__(self):
        super(BokehCtrl, self).__init__()

        self.lock = threading.Lock
        self.document = None

        self.pallete = self.MAIN_PALLETE

        # parent controller
        self.parent = None

        # figure to keep in memory for future changes
        self.figure = None

        # symbols + captions
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
        self.sym_bkgcolor = None
        self.sym_visible = None
        self.sym_linesize = 2

        # filtered intensity
        self.filter_captions = 0.

        # point related data
        self.points = []
        self.pos_names = []

    def set_symbol_style(self, type, size, linesize, linecolor, bkgcolor, visible):
        """
        Sets parameters for the symbol
        :param type:
        :param size:
        :param linecolor:
        :param bkgcolor:
        :param visible:
        :return:
        """
        self.sym_type = type
        self.sym_size = size
        self.sym_linesize = linesize
        self.sym_linecolor = linecolor
        self.sym_bkgcolor = bkgcolor
        self.sym_visible = visible

    def set_caption_style(self, xoffset, yoffset,  font, fontsize, color, bkgcolor, visible):
        """
        Sets parameters for caption
        :param xoffset:
        :param yoffset:
        :param fontsize:
        :param font:
        :param color:
        :param bkgcolor:
        :return:
        """
        self.cap_xoffset = xoffset
        self.cap_yoffset = yoffset
        self.cap_fontsize = fontsize
        self.cap_font = font
        self.cap_color = color
        self.cap_bkgcolor = bkgcolor
        self.cap_visible = visible

    def add_points(self, data):
        """
        Sets a list of points to show
        :param data:
        :return:
        """
        self.points = list(data)

    def debug(self, msg):
        if self.parent is not None:
            self.parent.debug(msg)

        print(msg)

    @gen.coroutine
    def _add_graph(self, new_data):
        """
        Adds a graph if absent and replaces the old one with a new one
        :return:
        """
        # remove old widget
        #self.debug(f"Update started {self.document}")
        data, palette, minimum, maximum, binvert_colormap = new_data

        # keep the same zoom in region
        x_range, y_range = None, None
        if self.figure is not None:
            x_range = self.figure.x_range
            y_range = self.figure.y_range

        self.pallete = palette

        root_layout = self.document.get_model_by_name(self.MAIN_LAYOUT)
        #self.debug(f"Got Root {root_layout}")

        sublayouts = root_layout.children
        #self.debug(f"Got sub layout {sublayouts}")

        plot = self.document.get_model_by_name(self.NAME_DATA)
        #self.debug(f"Plot removed {plot}")
        sublayouts.remove(plot)

        tpalette = self.prep_palette(palette, binvert_colormap)

        if data is not None:
            # making new plot image

            colormapper = LinearColorMapper(
                palette=tpalette, low=minimum, high=maximum,
            )

            tp = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")], width=1000, height=1000)
            self.figure = tp
            tp.x_range.range_padding = tp.y_range.range_padding = 0

            tr = tp.image(image=[data], x=0, y=0, dw=data.shape[0], dh=data.shape[1],
                          color_mapper=colormapper, level="image")

            # ticks
            tp.yaxis.major_label_text_font_size = "2em"
            tp.xaxis.major_label_text_font_size = "2em"
            tp.xaxis.major_label_text_font_size = "2em"
            tp.xaxis.axis_line_width = 2
            tp.yaxis.axis_line_width = 2
            tp.xaxis.major_tick_line_width = 2
            tp.yaxis.major_tick_line_width = 2
            tp.xaxis.minor_tick_line_width = 2
            tp.yaxis.minor_tick_line_width = 2

            ar = LinearAxis()
            ar.minor_tick_line_width = 2
            ar.major_label_text_font_size = "2em"
            ar.minor_tick_line_width = 2
            ar.axis_line_width = 2

            at = LinearAxis()
            at.minor_tick_line_width = 2
            at.major_label_text_font_size = "2em"
            at.minor_tick_line_width = 2
            at.axis_line_width = 2

            tp.add_layout(at, 'above')
            tp.add_layout(ar, 'right')

            if x_range is not None:
                tp.x_range = x_range

            if y_range is not None:
                tp.y_range = y_range

            tp.grid.grid_line_width = 0

            # captions
            if len(self.points) > 0:
                xs, ys = [], []
                names = []
                for point in self.points:
                    if isinstance(point,CrysalisPeak):
                        xs.append(point.detx)
                        ys.append(point.dety)
                        h,k,l = int(point.h), int(point.k), int(point.l)

                        name = ""
                        if self.filter_captions < point.intensity:
                            name = f"({h}, {k}, {l})"

                        names.append(name)
                        self.pos_names.append(f"{xs[-1]}\t{ys[-1]}\t{h}\t{k}\t{l}")

                if len(xs) > 0:
                    pts_data = ColumnDataSource(data=dict(x=xs,
                                    y=ys, names=names))

                    try:
                        if self._test_symdata() and self.sym_visible:
                                tp.scatter(x='x', y='y', size=self.sym_size, source=pts_data, fill_color=self.sym_bkgcolor,
                                           line_color=self.sym_linecolor, marker=self.sym_type, line_width=self.sym_linesize)


                        if self._test_captiondata() and self.cap_visible:
                            labels = LabelSet(x='x', y='y', text='names',
                                              x_offset=self.cap_xoffset, y_offset=self.cap_yoffset, source=pts_data, render_mode='canvas', visible=self.cap_visible,
                                              text_color=self.cap_color, text_font=self.cap_font, text_font_size=self.cap_fontsize,
                                              background_fill_color=self.cap_bkgcolor)

                            tp.add_layout(labels)
                    except Exception as e:
                        self.debug(f"Error: {e}")

            sublayouts.append(row(tp, name=self.NAME_DATA))

        #self.debug("Update finished")

    def _test_captiondata(self):
        """
        Tests if all data defining captions is present
        :return:
        """
        return self._test_data((self.cap_visible, self.cap_color, self.cap_font, self.cap_fontsize,
                                self.cap_xoffset,self.cap_yoffset,self.cap_visible))

    def _test_symdata(self):
        """
        Tests if all data defining points is present
        :return:
        """
        return self._test_data((self.sym_visible, self.sym_size, self.sym_type, self.sym_linecolor, self.sym_bkgcolor))

    def _test_data(self, tlist):
        """
        Performes a test if all data necessary for point display is present
        :return:
        """
        res =True
        for el in tlist:
            if el is None:
                res = False
                break
        return res

    def prep_palette(self, pname, binverse=False):
        """
        Prepares a palette based on a name
        :param pname:
        :return:
        """
        res = palettes.grey(256)

        if pname == 'Greys256':
            res = palettes.grey(256)
        elif pname == 'Inferno256':
            res = palettes.inferno(256)
        elif pname == 'Magma256':
            res = palettes.magma(256)
        elif pname == 'Plasma256':
            res = palettes.plasma(256)
        elif pname == 'Viridis256':
            res = palettes.viridis(256)
        elif pname == 'Cividis256':
            res = palettes.cividis(256)
        elif pname == 'Turbo256':
            res = palettes.turbo(256)
        elif pname == 'Bokeh8':
            res = palettes.small_palettes['Bokeh'][8]
        elif pname == 'Spectral11':
            res = palettes.small_palettes['Spectral'][11]
        elif pname == 'RdGy11':
            res = palettes.small_palettes['RdGy'][11]
        elif pname == 'PiYG11':
            res = palettes.small_palettes['PiYG'][11]

        if binverse:
            res = res[::-1]
        return res

    def add_graph(self, data, palette=None, minimum=None, maximum=None, binvertcmap=None):
        """
        Wrapper adding a callack to bokeh app
        :param data:
        :return:
        """
        tdata = [data, palette, minimum, maximum, binvertcmap]

        #self.debug(f"Adding data {data}, {(palette, minimum, maximum)}")
        self.document.add_next_tick_callback(partial(self._add_graph, new_data=tdata))
        # self.debug(f"Added data")

    def get_instance(self=None):
        global BOKEHCTRL

        if BOKEHCTRL is None:
            if self is None:
                BOKEHCTRL = BokehCtrl()
            else:
                BOKEHCTRL = self

        return BOKEHCTRL

