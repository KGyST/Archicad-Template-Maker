import Tkinter as tk

acIcons = '''
#define AcIcons_width 64
#define AcIcons_height 12
static unsigned char AcIcons_bits[] = {
   0x06, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1e, 0x00, 0xf8, 0x0f,
   0x80, 0x1f, 0x00, 0xc6, 0x3c, 0x0c, 0x00, 0x00, 0x80, 0x31, 0x00, 0xc6,
   0x70, 0x06, 0xf8, 0x03, 0x80, 0x31, 0x00, 0xc6, 0xe0, 0x03, 0x00, 0x08,
   0x80, 0x1f, 0x00, 0xc6, 0xc0, 0x01, 0x00, 0x18, 0x80, 0x31, 0x00, 0xc6,
   0xe0, 0x03, 0xe0, 0x3f, 0x80, 0x31, 0x00, 0xc6, 0x70, 0x06, 0xe0, 0x3f,
   0x80, 0x31, 0x00, 0xc6, 0x38, 0x04, 0x00, 0x18, 0x80, 0x31, 0x00, 0xc6,
   0x1c, 0x08, 0x00, 0x08, 0x80, 0x1f, 0x00, 0x7c, 0x1c, 0x00, 0xf8, 0x03,
   0x00, 0x00, 0x00, 0x00, 0x08, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
'''


class Panel1(tk.Frame):
    def __init__(self):
        tk.Frame.__init__(self)
        self.top = self.winfo_toplevel()
        i = tk.BitmapImage(data=acIcons, foreground="black", background="white", )

        f = tk.Label(image=i)
        f.i = i
        f.grid({"row": 0, "column": 0, })


def main():
    Panel1().top.mainloop()

if __name__ == "__main__":
    main()

