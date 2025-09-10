# LED Scales

A Python-based tool for generating LED scale patterns.

## Project Structure

The project is split into two main components, each with its own virtual environment:
1. CAD Generation (`venv-cad`) - For creating 3D printable scales and panel layouts
2. LED Control (`venv-led`) - For controlling the LED patterns through a web interface

## Virtual Environments

The project uses separate virtual environments for each component to keep dependencies clean and isolated:

- `venv-cad` - Contains dependencies for CAD generation (numpy, openpyscad, scipy)
- `venv-led` - Contains dependencies for LED control (Flask, WebSocket, etc.)

Virtual environments are created and managed automatically when you run the respective commands.

## How to generate files

1. Open `config.py` and set the parameters to your liking. Be sure to update `scad_path` to the path of your OpenSCAD installation.
2. Set up both virtual environments: `python main.py setup`
3. Run `python main.py all` to generate all the necessary files
   - This will automatically use the CAD virtual environment

## Development

- For LED development: `python main.py dev` 
  - Starts a development server with auto-reload
  - Uses the LED virtual environment
- For CAD development: `python main.py generate` (or `2d`/`3d`)
  - Uses the CAD virtual environment
- For linting: `python main.py lint`
  - Uses the CAD virtual environment (contains pylint)

## How to use

1. Inspect the `cad/out` directory to see if the results are satisfactory. Adjust `config.py` if necessary. Also use `python main.py leds-mock` to see what the LEDs will look like.
2. 3D print the tiles in `cad/out/tiles/`. Each tile can be printed on a single build plate. Keep them separated!
3. Order panels (material is up to you, I went with alupanel) with dimensions as outputted by the `all` command above. I'd recommend 3+mm thick.
4. Print out the template in `cad/out/panels/` onto paper.
5. Choose and order LEDs. I went with WS2812B strings (specifically [these](https://aliexpress.com/item/33044727740.html?spm=a2g0o.order_list.order_list_main.11.99da79d2ioNQ83&gatewayAdapt=glo2nld))
6. Drill holes for the LEDs on the panels (see template for location). Hole size should of course be the same as the LED. Mark the orientation of scales on the panels (I used a knife through the paper).
7. Print diffusers for the LEDs.
8. Wire LEDs through the back of the holes, put a diffuser on the front of the holes, use hot glue to stick them in place.
9. Assemble the scales on the marked locations. By starting out from the middle and simply going through print order you'll increase the curve as you go. Alternatively use `out/led-scales-py.positioning.scad` to get exact locations.
10. Wire LEDs to the power supply.
11. Get a raspberry pi and run the server (`python main.py leds`). Visit the web page to both see a preview and to control the effects.
12. Turn on the power and enjoy!