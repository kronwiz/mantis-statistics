# Mantis Statistics

## Introduction

This project is composed of:

- the main application written in Python;
- a form written in PHP that integrates into Mantis GUI.

The application uses the bug history table to check which bugs have not been resolved by a user in due time. By "due time" I mean a duration in days that can be set in the application using the command line parameters. There are three possible durations associated to three different bug priorities: normal, high and urgent. If a bug has not been processed in due time depending on its priority I call it an "expired" bug.

There's also another concept to be explained, and it's what I call a "transition". A transition is when a bug changes status going from a start status to an end status. For example a transition is when a bug goes from the "assigned" to the "resolved" status. In the application you can select which is the transition you would like to check. So you can ask which are the bugs that haven't been transitioned from assigned to resolved in due time, or the bugs which haven't been transitioned from resolved to closed in due time, or a transition between two custom states you added to Mantis.

There are command line parameters to choose the due times, the transition to be checked, the user to be checked, and so on. The details are here: [Usage](../../wiki/Usage)

Having chosen the user, the transition and the due times, the application is capable of two different outputs:

- a list of the expired bugs grouped by project;
- a statistic on the numbers of expired bugs grouped by project, year and month.

The list of expired bugs shows for each bug the id, summary, priority and days elapsed; in the HTML format you can click on the bug id to open the bug detail page in Mantis.

![Expired bugs report](https://cloud.githubusercontent.com/assets/6813780/6634816/269def66-c95e-11e4-81aa-eb4f42657ffc.png)

The statistics page shows a cell for each project, year and month containing two numbers: the number of expired bugs in the period and the total number of bugs.

![Expired bugs statistics](https://cloud.githubusercontent.com/assets/6813780/6634817/26a469cc-c95e-11e4-9146-06cb2ec1dac5.png)

Both reports can be output in **various formats**:

- **ascii**: suitable for a terminal output;
- **html**: this is the format used to display the output in Mantis GUI;
- **html standalone**: this is similar to the previous one but contains also the CSS definitions, and the links to Mantis bug detail page are absolute; this format is thought to be attached to a mail to be sent as a report;
- **csv**: it's a CSV format to be imported into spreadsheets.

I provide also a PHP form that integrates into Mantis GUI and that can be accessed as a custom menu item. The form drives the Python application using the same command line parameters you use in a terminal. Obviously the form can be customized at your will.

![Form](https://cloud.githubusercontent.com/assets/6813780/6634818/26a9930c-c95e-11e4-9acc-65a4473c676b.png)


## Installation

To install the application and the Mantis form see here: [Installation](../../wiki/Installation)


## LICENSE

This library is under the GNU GENERAL PUBLIC LICENSE Version 3. For more information about using/distributing the library see [http://www.gnu.org/copyleft/gpl.html](http://www.gnu.org/copyleft/gpl.html).

The above copyright notice, the licence and the following disclaimer shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
