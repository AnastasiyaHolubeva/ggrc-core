/*
    Copyright (C) 2020 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canMap from 'can-map';
import Ctrl from '../modals/archive-modal-controller';
import * as Helpers from '../../plugins/utils/modals';

describe('ToggleArchive modal', function () {
  'use strict';

  describe('click() event', function () {
    let ctrlInst;
    let $element;
    let event;

    beforeEach(() => {
      $element = $('<div data-modal_form="">' +
        '<a data-dismiss="modal"></a>' +
        '</div>');

      ctrlInst = {
        notifyArchivingResult: jasmine.createSpy(),
        element: $element,
        options: {
          instance: new canMap({
            refresh: jasmine.createSpy('save')
              .and.returnValue(new Promise(() => {})),
          }),
        },
      };

      spyOn(Helpers, 'bindXHRToButton');
      event = Ctrl.prototype['a.btn[data-toggle=archive]:not(:disabled) click']
        .bind(ctrlInst);
    });

    it('calls notifyArchivingResult() and bindXHRToButton()', () => {
      event($element);
      expect(Helpers.bindXHRToButton).toHaveBeenCalled();
      expect(ctrlInst.notifyArchivingResult).toHaveBeenCalled();
    });
  });

  describe('notifyArchivingResult() method', () => {
    let notifyArchivingResult;
    let ctrlInst;
    let instance;

    beforeEach(() => {
      instance = new canMap({ });

      ctrlInst = {
        options: {
          instance: instance,
        },
      };

      notifyArchivingResult =
        Ctrl.prototype.notifyArchivingResult.bind(ctrlInst);
    });

    it('calls archive() after instance.refresh() has resolved',
      async () => {
        ctrlInst.archive = jasmine.createSpy()
          .and.returnValue(Promise.resolve());
        ctrlInst.displaySuccessNotify = jasmine.createSpy()
          .and.returnValue(Promise.resolve());

        await notifyArchivingResult(Promise.resolve());

        expect(ctrlInst.archive).toHaveBeenCalled();
      });

    it('calls displaySuccessNotify() method' +
      'if instance.save() hasn\'t rejected', async () => {
      ctrlInst.archive = jasmine.createSpy()
        .and.returnValue(Promise.resolve());
      ctrlInst.displaySuccessNotify = jasmine.createSpy()
        .and.returnValue(Promise.resolve());

      await notifyArchivingResult(Promise.resolve());

      expect(ctrlInst.displaySuccessNotify).toHaveBeenCalled();
    });

    it('calls displayErrorNotify() method if instance.refresh() has rejected',
      async () => {
        ctrlInst.archive = jasmine.createSpy();
        ctrlInst.displaySuccessNotify = jasmine.createSpy();
        ctrlInst.displayErrorNotify = jasmine.createSpy();

        await notifyArchivingResult(Promise.reject());

        expect(ctrlInst.archive).not.toHaveBeenCalled();
        expect(ctrlInst.displaySuccessNotify).not.toHaveBeenCalled();
        expect(ctrlInst.displayErrorNotify).toHaveBeenCalled();
      });

    it('calls displayErrorNotify() method if instance.save() has rejected',
      async () => {
        ctrlInst.archive = jasmine.createSpy()
          .and.returnValue(Promise.reject());
        ctrlInst.displaySuccessNotify = jasmine.createSpy();
        ctrlInst.displayErrorNotify = jasmine.createSpy();

        await notifyArchivingResult(Promise.resolve());

        expect(ctrlInst.archive).toHaveBeenCalled();
        expect(ctrlInst.displaySuccessNotify).not.toHaveBeenCalled();
        expect(ctrlInst.displayErrorNotify).toHaveBeenCalled();
      });
  });

  describe('archive() method', () => {
    let archive;
    let ctrlInst;
    let instance;

    beforeEach(() => {
      instance = new canMap({
        save: jasmine.createSpy(),
      });

      ctrlInst = {
        options: {
          instance: instance,
        },
      };

      archive = Ctrl.prototype.archive.bind(ctrlInst);
    });

    it('sets archived attribute to true', () => {
      instance.attr('archived', false);

      archive();

      expect(instance.attr('archived')).toBe(true);
    });

    it('calls instance.save() method', () => {
      archive();

      expect(instance.save).toHaveBeenCalled();
    });
  });

  describe('displaySuccessNotify() method', () => {
    let displaySuccessNotify;
    let ctrlInst;
    let instance;
    let successMessage;
    const DISPLAY_NAME = 'DISPLAY NAME';

    beforeEach(() => {
      instance = new canMap({
        display_name() {
          return DISPLAY_NAME;
        },
      });

      ctrlInst = {
        options: {
          instance: instance,
        },
      };

      spyOn($.fn, 'trigger').and.callThrough();

      successMessage = DISPLAY_NAME + ' archived successfully';

      displaySuccessNotify =
        Ctrl.prototype.displaySuccessNotify.bind(ctrlInst);
    });

    it('displays success message', () => {
      displaySuccessNotify();

      expect($.fn.trigger)
        .toHaveBeenCalledWith('ajax:flash', {success: [successMessage]});
    });

    it('triggers modal success if element exists', () => {
      ctrlInst.element = {
        trigger: jasmine.createSpy(),
      };

      displaySuccessNotify();

      expect(ctrlInst.element.trigger)
        .toHaveBeenCalledWith('modal:success', instance);
    });
  });

  describe('displayErrorNotify() method', () => {
    let displayErrorNotify;
    let errorMessage;
    let error;

    beforeEach(() => {
      spyOn($.fn, 'trigger').and.callThrough();

      errorMessage = 'Internal error';

      error = {responseText: errorMessage};

      displayErrorNotify = Ctrl.prototype.displayErrorNotify;
    });

    it('displays error message', () => {
      displayErrorNotify(error);

      expect($.fn.trigger)
        .toHaveBeenCalledWith('ajax:flash', {error: [errorMessage]});
    });
  });
});
